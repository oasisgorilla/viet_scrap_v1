### scraper/directive_scraper.py ###
# 행정지시문서 수집 코드 (공통 베이스 사용)
from scraper.base_scraper_core import BaseScraper
from log_util import setup_logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re
import time
import pandas as pd
import os
from pathlib import Path
from math import ceil

# ----------- 전역 설정값 ------------
BASE_URL = "https://chinhphu.vn"
START_URL = f"{BASE_URL}/he-thong-van-ban?classid=2&mode=1"
OUTPUT_DIR = "output/directive"
WAIT_TIME = 10
DOCS_PER_PAGE = 50
PAGE_CHUNK_SIZE = 10

LOGGER = setup_logger(__name__, f"{OUTPUT_DIR}/log/directive_scrapper.log")

class DirectiveScraper(BaseScraper):
    """행정지시문서 스크래퍼 - 공통 베이스 사용"""
    
    def __init__(self):
        super().__init__(BASE_URL, START_URL, OUTPUT_DIR, WAIT_TIME, DOCS_PER_PAGE, LOGGER)
        self.info_results = []
        self.temp_info_results = []

    def run(self):
        """실행 메인 로직"""
        try:
            self.driver.delete_all_cookies()
            
            # 총 문서 수와 페이지 수 계산
            total_docs, total_page_number = self.extract_total_pages()
            
            start_page = 1
            output_dir = Path(self.output_dir) / "info"
            os.makedirs(output_dir, exist_ok=True)

            # 전체 페이지 수만큼 반복
            for current_page_number in range(start_page, total_page_number + 1):
                try:
                    if not self.safe_go_to(self.go_to_page, current_page_number, total_page_number):
                        self.logger.error(f"페이지 {current_page_number} 이동 실패")
                        continue
                except:
                    self.logger.error(f"페이지 {current_page_number} safe_go_to_page 실패")
                    continue

                directive_urls = self.extract_links_from_current_page(current_page_number)

                for idx, directive_url in enumerate(directive_urls):
                    try:
                        info = self.safe_extract(self.extract_details, directive_url, 
                                               current_page_number, idx + 1, len(directive_urls))
                        if info:
                            self.temp_info_results.append(info)
                            self.logger.info(f"[{idx+1}/{len(directive_urls)}] 세부정보 처리 완료: {directive_url}")
                        else:
                            self.logger.error(f"[{idx+1}/{len(directive_urls)}] 세부정보 없음: {directive_url}")

                        self.driver.back()
                        time.sleep(1)
                    except Exception as e:
                        self.logger.error(f"[{idx+1}/{len(directive_urls)}] 개별문서 예외: {directive_url} ({e})")

                # chunk size마다 중간저장
                if current_page_number % PAGE_CHUNK_SIZE == 0 or current_page_number == total_page_number:
                    end_page = current_page_number
                    file_name = f"directive_info_output_{start_page:03d}_{end_page:03d}.xlsx"
                    file_path = os.path.join(output_dir, file_name)

                    # 누적
                    self.info_results.extend(self.temp_info_results)
                    
                    # 엑셀로 저장
                    if self.info_results:
                        df1 = pd.DataFrame(self.info_results)
                        df1.to_excel(file_path, index=False)
                        self.logger.info(f"저장됨: {file_path}")
                    else:
                        self.logger.error(f"저장할 데이터 없음: {file_path}")

                    self.temp_info_results = []

            self.logger.info("directive info 병합 시작")
            self.merge_excel("info", ['docid'])
            
            # 수집 실패한 url csv 저장
            if self.failed_urls:
                failed_path = Path(self.output_dir) / "log" / "failed_urls.csv"
                pd.DataFrame({"url": self.failed_urls}).to_csv(failed_path, index=False, encoding="utf-8")
                self.logger.warning(f"수집 실패한 URL {len(self.failed_urls)}건 저장됨: {failed_path}")

        finally:
            self.driver.quit()

    # ===== 행정지시문서 전용 메서드들 =====
    
    def extract_total_pages(self):
        """총 문서 수를 바탕으로 페이지 수 계산"""
        try:
            self.driver.get(self.start_url)
            total_text = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tr.grid-pager th.th-detail span")
            )).text  # 예: "1 - 50 | 46955"
            total_docs = int(total_text.split('|')[-1].strip())
            return total_docs, ceil(total_docs / self.docs_per_page)
        except Exception as e:
            self.logger.error(f"총 문서 수 추출 실패: {e}")
            return 0, 0

    def extract_links_from_current_page(self, page):
        """현재 페이지에서 상세 링크 수집"""
        urls = []
        try:
            table = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "div.document-content table.table.search-result"
            )))
            rows = table.find_elements(By.TAG_NAME, "tr")[1:-2]  # 헤더, 페이지네이션 제외

            for idx, row in enumerate(rows, start=1):
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) >= 1:
                    try:
                        a_tag = tds[0].find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")
                        full_url = self.base_url + href if href.startswith("/") else href
                        urls.append(full_url)
                    except:
                        self.logger.info(f"{page}페이지 {idx}번 문서 - ⚠️ <a> 태그가 없는 tr 무시됨")
        except Exception as e:
            self.logger.error(f"페이지 {page} 상세 링크 수집 실패: {e}")
        
        self.logger.info(f"{page}페이지에서 {len(urls)}개 링크 수집 완료")
        return urls

    def extract_details(self, directive_url, page, idx, total_url):
        """상세정보 수집"""
        try:
            self.driver.get(directive_url)
            self.wait.until(EC.presence_of_element_located((By.ID, "ctrl_190596_91_Content")))

            # docid 추출
            parsed = urlparse(directive_url)
            q = {k.lower(): v for k, v in parse_qs(parsed.query).items()}
            docid = (q.get("docid", [None])[0] or "").strip()
            if not docid:
                m = re.search(r"[?&]docid=(\d+)", directive_url, flags=re.I)
                docid = m.group(1) if m else "-"

            info = {
                "docid": docid,
                "문서코드": "-", "발행일": "-", "발효일": "-", "문서유형": "-",
                "발급기관": "-", "서명자": "-", "문서명": "-",
                "다운로드링크": "-", "url": directive_url
            }

            # 테이블에서 정보 추출
            try:
                table = self.driver.find_element(By.CSS_SELECTOR, "div#ctrl_190596_91_Content table")
            except:
                table = self.driver.find_element(By.CSS_SELECTOR, "div#block_detail table:nth-of-type(2)")
            
            rows = table.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                try:
                    tds = row.find_elements(By.TAG_NAME, "td")
                    if len(tds) < 2:
                        continue
                    label = tds[0].text.strip()
                    value = tds[1].text.strip()
                except:
                    self.logger.info(f"{page} 페이지 {idx}번 문서 내용 중 일부 누락: {directive_url}")
                    continue

                if label == "Số ký hiệu":
                    info["문서코드"] = value
                elif label == "Ngày ban hành":
                    try:
                        date_obj = datetime.strptime(value, "%d-%m-%Y")
                        info["발행일"] = date_obj.strftime("%Y-%m-%d")
                    except:
                        info["발행일"] = "-"
                elif label == "Ngày có hiệu lực":
                    try:
                        date_obj = datetime.strptime(value, "%d-%m-%Y")
                        info["발효일"] = date_obj.strftime("%Y-%m-%d")
                    except:
                        info["발효일"] = "-"
                elif label == "Loại văn bản":
                    info["문서유형"] = value
                elif label == "Cơ quan ban hành":
                    info["발급기관"] = value
                elif label == "Người ký":
                    info["서명자"] = value
                elif label == "Trích yếu":
                    info["문서명"] = value
                elif label == "Tài liệu đính kèm":
                    try:
                        a_dl = row.find_element(By.TAG_NAME, "a")
                        info["다운로드링크"] = a_dl.get_attribute("href") or "-"
                    except:
                        info["다운로드링크"] = "-"

            self.logger.info(f"{page}페이지 [{idx}/{total_url}] 문서 상세 수집 완료")
            return info

        except Exception as e:
            self.logger.error(f"페이지 {page} [{idx}/{total_url}] 문서 상세 수집 실패: {directive_url} | {e}")
            return {}

    def go_to_page(self, target_page: int, total_page_number: int):
        """페이지 이동 함수"""
        def parse_page_buttons():
            """현재 페이지에서 클릭 가능한 페이지 버튼 정보 추출"""
            pager_tds = self.driver.find_elements(By.CSS_SELECTOR, 
                "table.table.search-result tr.grid-pager td table tr td")
            buttons = []

            for td in pager_tds:
                try:
                    a_tag = td.find_element(By.TAG_NAME, "a")
                    label = a_tag.text.strip()
                    href = a_tag.get_attribute("href")

                    match = re.search(r"Page\$(\d+)", href)
                    if match:
                        page_num = int(match.group(1))
                        buttons.append({
                            "label": label,
                            "page": page_num,
                            "element": a_tag
                        })
                except:
                    continue

            return buttons

        max_tries = total_page_number + 1
        tries = 0

        while tries < max_tries:
            try:
                self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "table.table.search-result tr.grid-pager")))
            except:
                self.logger.critical("페이지네이션 로드 실패")
                return False

            try:
                ad = self.driver.find_element(By.ID, "yhy-append")
                self.driver.execute_script("arguments[0].remove();", ad)
            except:
                pass

            buttons = parse_page_buttons()
            page_nums = [b["page"] for b in buttons]

            if target_page in page_nums:
                for b in buttons:
                    if b["page"] == target_page:
                        self.driver.execute_script("arguments[0].click();", b["element"])
                        time.sleep(2)
                        return True
            else:
                forward = [b for b in buttons if b["page"] > target_page]
                backward = [b for b in buttons if b["page"] < target_page]

                if backward:
                    self.driver.execute_script("arguments[0].click();", backward[-1]["element"])
                elif forward:
                    self.driver.execute_script("arguments[0].click();", forward[0]["element"])
                else:
                    self.logger.critical(f"{target_page}페이지 버튼을 찾을 수 없습니다.")
                    return False

            time.sleep(2)
            tries += 1

        self.logger.critical(f"{target_page} 페이지 이동 실패 - 최대 시도 횟수 초과")
        return False

    def get_all_directive_urls(self, total_pages):
        """행정지시문서 목록에서 전체 URL 목록 수집 (업데이터용)"""
        new_urls = []
        for page in range(1, total_pages + 1):
            if self.safe_go_to(self.go_to_page, page, total_pages):
                urls = self.extract_links_from_current_page(page)
                new_urls.extend(urls)
        self.logger.info(f"총 {len(new_urls)} 개의 문서를 확인하였습니다.")
        return new_urls

if __name__ == "__main__":
    """테스트용 실행부"""
    pass