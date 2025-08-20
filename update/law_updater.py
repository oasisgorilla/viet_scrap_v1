### update/law_updater.py ###
# 중앙정부/지방정부 법령 통합 업데이터

import pandas as pd
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime
from typing import Literal
import time

class LawUpdater:
    """중앙/지방 법령정보 통합 업데이터"""
    
    def __init__(self, mode: Literal["central", "local"], scraper, logger=None):
        self.mode = mode
        self.scraper = scraper
        self.logger = logger or scraper.logger

    def run(self):
        """업데이터 실행"""
        try:
            self.scraper.driver.delete_all_cookies()
            
            if self.mode == "central":
                self._run_central_update()
            else:  # local
                self._run_local_update()
                
        finally:
            self.scraper.driver.quit()

    def _run_central_update(self):
        """중앙정부 법령 업데이트"""
        # 기존 URL 목록 로드
        existing_urls = self._load_existing_urls()
        
        try:
            self.scraper.driver.get(self.scraper.start_url)
            
            # 최신 20페이지 URL 수집
            all_urls = self.scraper.get_all_law_urls(20)
            urls_to_collect = [url for url in all_urls if url not in existing_urls]
            self.logger.info(f"[{self.mode}] 신규 업데이트된 url: {len(urls_to_collect)}건")
            
            # 실패 URL 추가
            urls_to_collect = self._add_failed_urls(urls_to_collect)
            
            # URL 수집 및 처리
            self._process_update_urls(urls_to_collect)
            
        except Exception as e:
            self.logger.error(f"[{self.mode}] 업데이트 중 오류: {e}")

    def _run_local_update(self):
        """지방정부 법령 업데이트"""
        # 기존 URL 목록 로드
        existing_urls = self._load_existing_urls()
        
        try:
            self.scraper.driver.get(self.scraper.start_url)
            
            # 지역 링크 수집
            self._collect_region_links()
            
            urls_to_collect = []
            
            # 각 지역별 URL 수집
            for region_idx, (region_code, region_url) in enumerate(self.scraper.region_links):
                self.scraper.start_url = region_url
                
                if not self.scraper.safe_go_to(self.scraper.go_to_law_list):
                    self.logger.error(f"[{region_code}] 문서목록으로 이동 실패")
                    continue
                
                self.logger.info(f"[{region_code}] 업데이트를 위해 최신 20개 페이지를 확인합니다.")
                current_urls = self.scraper.get_all_law_urls(20)
                current_urls_to_collect = [url for url in current_urls if url not in existing_urls]
                self.logger.info(f"[{region_code}] 신규 업데이트된 url: {len(current_urls_to_collect)}건")
                urls_to_collect.extend(current_urls_to_collect)
            
            self.logger.info(f"[{self.mode}] 전체 지역 신규 업데이트된 url: {len(urls_to_collect)}건")
            
            # 실패 URL 추가
            urls_to_collect = self._add_failed_urls(urls_to_collect)
            
            # URL 수집 및 처리
            self._process_update_urls(urls_to_collect)
            
        except Exception as e:
            self.logger.error(f"[{self.mode}] 업데이트 중 오류: {e}")

    def _collect_region_links(self):
        """지역 링크 수집 (지방정부용)"""
        try:
            li_tags = self.scraper.driver.find_elements(By.CSS_SELECTOR, 
                "div.list-diaphuong div.container tr:nth-child(2) li")
            for li in li_tags:
                try:
                    a_tag = li.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                    full_url = urljoin(self.scraper.base_url, href)
                    
                    parsed = urlparse(full_url)
                    region_code = parsed.path.strip("/")
                    
                    if not region_code or region_code.lower() == "tw":
                        continue
                        
                    self.scraper.region_links.append((region_code, full_url))
                except:
                    self.logger.info(f"지방 {li.text} <li>태그 데이터 추출 실패")
                    continue
        except Exception as e:
            self.logger.error(f"지역 링크 수집 실패: {e}")

    def _load_existing_urls(self):
        """기존 수집된 URL 목록 로드"""
        merged_file = Path(self.scraper.output_dir) / "info" / "merged_result.xlsx"
        existing_urls = set()
        
        if merged_file.exists():
            try:
                df_existing = pd.read_excel(merged_file)
                existing_urls = set(df_existing["url"].dropna().unique())
                self.logger.info(f"기존 수집된 URL: {len(existing_urls)}건")
            except Exception as e:
                self.logger.error(f"기존 URL 로드 실패: {e}")
        
        return existing_urls

    def _add_failed_urls(self, urls_to_collect):
        """실패 URL 추가"""
        failed_urls_path = Path(self.scraper.output_dir) / "log" / "failed_urls.csv"
        
        if failed_urls_path.exists():
            try:
                failed_df = pd.read_csv(failed_urls_path)
                failed_urls = failed_df["url"].dropna().unique().tolist()
                urls_to_collect = list(set(urls_to_collect + failed_urls))
                self.logger.info(f"[{self.mode}] 기존 수집실패했던 url: {len(failed_urls)}건")
            except Exception as e:
                self.logger.error(f"failed_urls.csv 불러오기 실패: {e}")
        else:
            self.logger.info("failed_urls.csv 파일 없음 (처음 실행 또는 모든 수집 성공)")
        
        self.logger.info(f"[{self.mode}] 총 수집 대상 url: {len(urls_to_collect)}건")
        return urls_to_collect

    def _process_update_urls(self, urls_to_collect):
        """업데이트 URL 처리"""
        if not urls_to_collect:
            self.logger.info(f"[{self.mode}] 업데이트할 URL이 없습니다.")
            return

        # URL별 상세정보 수집
        for i, url in enumerate(urls_to_collect):
            self.logger.info(f"[{i+1}/{len(urls_to_collect)}] {url} 수집 시작")
            info, relations, download_link = self.scraper.safe_extract(
                self.scraper.extract_law_details, url)
            
            if info:
                self.scraper.info_results.append(info)
            if relations:
                self.scraper.relations_results.extend(relations)
            if download_link:
                self.scraper.download_link_results.extend(download_link)

        # 결과 저장
        self._save_update_results(urls_to_collect)

    def _save_update_results(self, urls_to_collect):
        """업데이트 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        
        # 기본정보 저장
        if self.scraper.info_results:
            df_info = pd.DataFrame(self.scraper.info_results)
            updated_file = Path(self.scraper.output_dir) / "info" / f"updated_result_{timestamp}.xlsx"
            df_info.to_excel(updated_file, index=False)
            
            success_rate = len(self.scraper.info_results) / len(urls_to_collect) * 100
            self.logger.info(f"수집 대상 {len(urls_to_collect)}건 중 "
                           f"{len(self.scraper.info_results)}건 수집 성공 ({success_rate:.1f}%)")
            
            # 병합
            self.logger.info("info 병합 시작")
            self.scraper.merge_excel("info", ['itemID'])
        else:
            self.logger.error("업데이트할 기본정보 데이터 없음")

        # 관계정보 저장
        if self.scraper.relations_results:
            df_relation = pd.DataFrame(self.scraper.relations_results)
            updated_file = Path(self.scraper.output_dir) / "relation" / f"updated_result_{timestamp}.xlsx"
            df_relation.to_excel(updated_file, index=False)
            self.logger.info(f"새로운 관계정보 {len(df_relation)}건 저장 완료: {updated_file}")
            
            # 병합
            self.logger.info("relations 병합 시작")
            self.scraper.merge_excel("relation", [])
        else:
            self.logger.error("업데이트할 관계정보 데이터 없음")

        # 다운로드 링크 저장
        if self.scraper.download_link_results:
            df_download_link = pd.DataFrame(self.scraper.download_link_results)
            updated_file = Path(self.scraper.output_dir) / "download_link" / f"updated_result_{timestamp}.xlsx"
            df_download_link.to_excel(updated_file, index=False)
            self.logger.info(f"새로운 다운로드링크 {len(df_download_link)}건 저장 완료: {updated_file}")
            
            # 병합
            self.logger.info("download_links 병합 시작")
            self.scraper.merge_excel("download_link", ['itemID', '다운로드 링크'])
        else:
            self.logger.error("업데이트할 다운로드 링크 데이터 없음")

        # 실패 URL 저장
        if self.scraper.failed_urls:
            failed_path = Path(self.scraper.output_dir) / "log" / "failed_urls.csv"
            pd.DataFrame({"url": self.scraper.failed_urls}).to_csv(
                failed_path, index=False, encoding="utf-8")
            self.logger.warning(f"수집 실패한 URL {len(self.scraper.failed_urls)}건 저장됨: {failed_path}")

        self.logger.info(f"[{self.mode}] 법령정보 업데이트 완료")