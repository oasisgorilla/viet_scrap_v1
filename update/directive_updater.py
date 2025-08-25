### central_law_updater.py ###
# 행정지시문서 업데이트 기능을 다룹니다.

from scraper.directive_scraper import DirectiveScraper
from log_util import setup_logger
import pandas as pd
import os
import time
from pathlib import Path
from datetime import datetime

class DirectiveUpdater:
    def __init__(self, scraper:DirectiveScraper):
        self.scraper = scraper
        self.logger = setup_logger(__name__, f"output/directive/log/directive_updater.log")
    def run(self):
        self.scraper.driver.delete_all_cookies()
        # ---------- 수집된 행정지시문서 url 목록 로드 ----------
        directive_info_merged_file = Path(self.scraper.output_dir)/"info"/"merged_result.xlsx"
        directive_existing_urls = set([])
        if directive_info_merged_file.exists():
            directive_df_existing = pd.read_excel(directive_info_merged_file)
            directive_existing_urls = set(directive_df_existing["url"].dropna().unique())
        
        try:
            try:
                self.scraper.driver.get(self.scraper.start_url)
            except Exception as e:
                self.logger.info(f"[directive_updater.py, line 26] 첫 페이지 접근 실패 : {e}")
            all_urls = self.scraper.get_all_directive_urls(20) # 최신 20개 페이지만 수집
            urls_to_collect = [url for url in all_urls if url not in directive_existing_urls]
            self.logger.error(f"directive_updater.py | 신규 업데이트된 url: {len(urls_to_collect)}건")

            # 기존에 오류로 수집하지 못했던 url목록인 failed_urls.csv 확인하여 urls_to_collect에 추가
            # 만약 Path(self.scraper.output_dir)/"log"/failed_urls.csv 없으면 그냥 진행
            # urls_to_collect에 중복이 없도록 하기
            failed_urls_path = Path(self.scraper.output_dir)/"log"/"failed_urls.csv"
            if failed_urls_path.exists():
                try:
                    failed_df = pd.read_csv(failed_urls_path)
                    failed_urls = failed_df["url"].dropna().unique().tolist()
                    # 중복 제거하여 추가
                    urls_to_collect = list(set(urls_to_collect + failed_urls))
                    self.logger.warning(f"directive_updater.py | 기존 수집실패했던 url: {len(failed_urls)}건")
                except Exception as e:
                    self.logger.error(f"failed_urls.csv 불러오기 실패: {e}")
            else:
                self.logger.info("failed_urls.csv 파일 없음 (처음 실행 또는 모든 수집 성공)")
            self.logger.error(f"directive_updater.py | 신규 업데이트된 url과 기존 수집실패했던 url 중 중복을 제거한 {len(urls_to_collect)}건의 url 수집시도")

            for i, url in enumerate(urls_to_collect):
                self.logger.info(f"[{i+1}/{len(urls_to_collect)}] {url} 수집 시작")
                try:
                    info = self.scraper.safe_extract(self.scraper.extract_details, url, 0, i+1, len(urls_to_collect))
                    if info:
                        self.scraper.info_results.append(info)
                        self.logger.info(f"[{i+1}/{len(urls_to_collect)}] 세부정보 처리 완료 : {url}")
                    else:
                        msg = f"[{i+1}/{len(urls_to_collect)}] 세부정보 없음 : {url}"
                        self.logger.info(msg)

                    self.scraper.driver.back()
                    time.sleep(1)
                except Exception as e:
                    msg = f"[{i+1}/{len(urls_to_collect)}] 예외 발생 : {url} ({e})"
                    self.logger.error(msg)
            
            # 엑셀로 저장
            timestamp = datetime.now().strftime("%Y%m%d%H%M")
            output_dir = Path(self.scraper.output_dir)/"info"
            os.makedirs(output_dir, exist_ok=True)
            file_name = f"updated_result_{timestamp}.xlsx"
            file_path = os.path.join(output_dir, file_name)
            if self.scraper.info_results:
                df1 = pd.DataFrame(self.scraper.info_results)

                df1.to_excel(file_path, index=False)
                self.logger.error(f"수집 대상 {len(urls_to_collect)}건 중 {len(self.scraper.info_results)}건 수집 성공 ({len(self.scraper.info_results) / len(urls_to_collect) * 100:.1f}%)")
                #엑셀 병합
                self.logger.info("directive info 병합 시작")
                self.scraper.merge_excel("info", ['docid'])
            else:
                self.logger.error(f"업데이트할 세부정보 데이터 없음: {file_path}")
            
            # 수집 실패한 url csv 저장
            if self.scraper.failed_urls:
                failed_path = Path(self.scraper.output_dir)/"log"/"failed_urls.csv"
                pd.DataFrame({"url": self.scraper.failed_urls}).to_csv(failed_path, index=False, encoding="utf-8")
                self.logger.warning(f"수집 실패한 URL {len(self.scraper.failed_urls)}건 저장됨: {failed_path}")
        finally:
            self.scraper.driver.quit()