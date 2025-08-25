### scraper/law_scraper.py ###
# 중앙정부/지방정부 법령 통합 스크래퍼

from scraper.base_scraper_core import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse, parse_qs
import time
from pathlib import Path
import pandas as pd
import os
from math import ceil
from typing import Literal, List, Dict, Any, Tuple

class LawScraper(BaseScraper):
    """중앙/지방 법령정보 통합 스크래퍼"""
    
    def __init__(self, mode: Literal["central", "local"], logger=None, use_undetected=False):
        self.mode = mode
        
        # 모드별 설정
        base_url = "https://vbpl.vn"
        start_url = f"{base_url}/TW/Pages/home.aspx"
        output_dir = f"output/{mode}_law"
        wait_time = 10
        docs_per_page = 30
        
        super().__init__(base_url, start_url, output_dir, wait_time, docs_per_page, logger, use_undetected)
        
        # 결과 저장용
        self.info_results = []
        self.relations_results = []
        self.download_link_results = []
        self.temp_info_results = []
        self.temp_relation_results = []
        self.temp_download_link_results = []
        
        # 지방정부용 지역 링크
        self.region_links = []

    def run(self):
        """실행 메인 로직"""
        try:
            self.driver.delete_all_cookies()
            
            if self.mode == "central":
                self._run_central()
            else:  # local
                self._run_local()
                
        finally:
            self.driver.quit()

    def _run_central(self):
        """중앙정부 법령 수집"""
        if not self.safe_go_to(self.go_to_law_list):
            self.logger.critical("중앙정부 문서목록으로 이동 실패")
            return

        try:
            total_docs_text = self.driver.find_element(By.CSS_SELECTOR, 
                "div#grid_vanban div.box-container div#tabVB_lv1 div.header ul li a.selected b").text
            total_docs = int(total_docs_text.replace(".", "").replace(",", "").strip())
            total_pages = ceil(total_docs / self.docs_per_page)
            self.logger.info(f"총 문서 수: {total_docs}, 총 페이지 수: {total_pages}")
        except Exception as e:
            self.logger.critical(f"문서 수 불러오기 중 오류: {e}")
            return

        self._process_pages(total_pages, "중앙")
        self._finalize_results()

    def _run_local(self):
        """지방정부 법령 수집"""
        # 지역 링크 수집
        self.driver.get(self.start_url)
        time.sleep(2)
        
        try:
            li_tags = self.driver.find_elements(By.CSS_SELECTOR, 
                "div.list-diaphuong div.container tr:nth-child(2) li")
            for li in li_tags:
                try:
                    a_tag = li.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                    full_url = urljoin(self.base_url, href)
                    
                    parsed = urlparse(full_url)
                    region_code = parsed.path.strip("/")
                    
                    if not region_code or region_code.lower() == "tw":
                        continue
                        
                    self.region_links.append((region_code, full_url))
                except:
                    self.logger.error(f"지방 {li.text} <li>태그 데이터 추출 실패")
                    continue
        except Exception as e:
            self.logger.critical(f"지역 링크 수집 실패: {e}")
            return

        # 각 지역별 처리
        for region_code, region_url in self.region_links:
            self.start_url = region_url
            self.logger.info(f"\n=== {region_code} 지역 처리 시작 ===")
            
            if not self.safe_go_to(self.go_to_law_list):
                self.logger.error(f"[{region_code}] 문서목록으로 이동 실패")
                continue

            try:
                total_docs_text = self.driver.find_element(By.CSS_SELECTOR, 
                    "div#grid_vanban div.box-container div#tabVB_lv1 div.header ul li a.selected b").text
                total_docs = int(total_docs_text.replace(".", "").replace(",", "").strip())
                total_pages = ceil(total_docs / self.docs_per_page)
                self.logger.info(f"[{region_code}] 총 문서 수: {total_docs}, 총 페이지 수: {total_pages}")
            except Exception as e:
                self.logger.error(f"[{region_code}] 문서 수 불러오기 중 오류: {e}")
                continue

            self._process_pages(total_pages, region_code)
            
            # 지역별 결과 초기화
            self.info_results = []
            self.relations_results = []
            self.download_link_results = []

        self._finalize_results()

    def _process_pages(self, total_pages: int, region_name: str):
        """페이지별 처리 공통 로직"""
        PAGE_CHUNK_SIZE = 10
        
        # 출력 디렉토리 생성
        output_dirs = {
            "info": Path(self.output_dir) / "info",
            "relation": Path(self.output_dir) / "relation", 
            "download_link": Path(self.output_dir) / "download_link"
        }
        for dir_path in output_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        start_page = 1
        chunk_start_page = start_page

        for page in range(chunk_start_page, total_pages + 1):
            self.logger.info(f"\n=== {region_name} 페이지 {page}/{total_pages} ===")
            
            # 페이지별 링크 수집
            detail_urls = self._extract_page_links(page)
            if not detail_urls:
                self.logger.error(f"페이지 {page} 링크 추출 실패, 스킵")
                continue

            # 상세정보 수집
            for i, detail_url in enumerate(detail_urls):
                try:
                    info, relations, download_link = self.safe_extract(
                        self.extract_law_details, detail_url)
                    
                    if info:
                        self.temp_info_results.append(info)
                        self.logger.info(f"[{i+1}/{len(detail_urls)}] 법률정보 처리 완료")
                    
                    if relations:
                        self.temp_relation_results.extend(relations)
                        self.logger.info(f"[{i+1}/{len(detail_urls)}] 관계정보 처리 완료")
                    
                    if download_link:
                        self.temp_download_link_results.extend(download_link)
                        self.logger.info(f"[{i+1}/{len(detail_urls)}] 다운로드링크 처리 완료")
                        
                except Exception as e:
                    self.logger.error(f"[페이지 {page}, 항목 {i+1}] 예외 발생: {e}")

            # 청크 단위로 저장
            if page % PAGE_CHUNK_SIZE == 0 or page == total_pages:
                self._save_chunk_results(start_page, page, region_name, output_dirs)
                chunk_start_page = page + 1

    def _extract_page_links(self, page: int) -> List[str]:
        """페이지에서 상세 링크 추출"""
        max_retry = 3
        detail_urls = []
        
        for retry in range(max_retry):
            try:
                if not self.safe_go_to(self.go_to_law_list):
                    continue
                    
                if page > 1:
                    self.wait.until(lambda d: d.execute_script(
                        "return typeof LoadPage === 'function';") == True)
                    self.driver.execute_script("LoadPage(arguments[0]);", page)
                
                self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ul.listLaw > li")))
                time.sleep(1.5)

                items = self.driver.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")
                if not items:
                    raise Exception("문서 항목 비어 있음")

                for item in items:
                    a_tag = item.find_element(By.TAG_NAME, "a")
                    href = a_tag.get_attribute("href")
                    detail_urls.append(href)

                self.logger.info(f"링크 {len(detail_urls)}개 추출 완료")
                break
                
            except Exception as e:
                self.logger.warning(f"링크 추출 재시도 {retry+1}/{max_retry}: {e}")
                time.sleep(5)
        
        return detail_urls

    def _save_chunk_results(self, start_page: int, end_page: int, region_name: str, output_dirs: Dict):
        """청크 결과 저장"""
        # 누적
        self.info_results.extend(self.temp_info_results)
        self.relations_results.extend(self.temp_relation_results)
        self.download_link_results.extend(self.temp_download_link_results)

        # 파일명 생성
        if self.mode == "local":
            prefix = f"{region_name}_"
        else:
            prefix = ""
            
        filenames = {
            "info": f"{prefix}info_output_{start_page:03d}_{end_page:03d}.xlsx",
            "relation": f"{prefix}relations_output_{start_page:03d}_{end_page:03d}.xlsx",
            "download_link": f"{prefix}download_link_output_{start_page:03d}_{end_page:03d}.xlsx"
        }

        # 저장
        data_sets = {
            "info": self.info_results,
            "relation": self.relations_results, 
            "download_link": self.download_link_results
        }
        
        for key, data in data_sets.items():
            if data:
                df = pd.DataFrame(data)
                file_path = output_dirs[key] / filenames[key]
                df.to_excel(file_path, index=False)
                self.logger.info(f"저장됨: {file_path}")
            else:
                self.logger.error(f"저장할 데이터 없음: {filenames[key]}")

        # 임시 결과 초기화
        self.temp_info_results = []
        self.temp_relation_results = []
        self.temp_download_link_results = []

    def _finalize_results(self):
        """최종 결과 처리"""
        # 엑셀 병합
        self.logger.info("info 병합 시작")
        self.merge_excel("info", ['itemID'])
        
        self.logger.info("relations 병합 시작")
        self.merge_excel("relation", ['regionID', 'itemID', 'relation_itemID', '관계유형'])
        
        self.logger.info("download_links 병합 시작")
        self.merge_excel("download_link", ['itemID', '다운로드 링크'])

        # ID 추가
        self._add_primary_keys()
        
        # 실패 URL 저장
        self._save_failed_urls()

    def _add_primary_keys(self):
        """관계정보, 다운로드 링크에 일련번호 추가"""
        def add_pk(file_path, pk_name="id"):
            if not file_path.exists():
                return
                
            df = pd.read_excel(file_path)
            if pk_name in df.columns:
                df = df.drop(columns=[pk_name])
            df.insert(0, pk_name, range(1, len(df) + 1))
            df.to_excel(file_path, index=False)

        merged_relation_path = Path(self.output_dir) / "relation" / "merged_result.xlsx"
        merged_download_path = Path(self.output_dir) / "download_link" / "merged_result.xlsx"

        add_pk(merged_relation_path)
        add_pk(merged_download_path)

    def _save_failed_urls(self):
        """실패한 URL 저장"""
        if not self.failed_urls:
            return
            
        failed_path = Path(self.output_dir) / "log" / "failed_urls.csv"
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        
        new_failed = pd.DataFrame({"url": sorted(set(u for u in self.failed_urls if u))})

        if failed_path.exists():
            try:
                old_failed = pd.read_csv(failed_path)
                combined = pd.concat([old_failed, new_failed], ignore_index=True)
                combined = combined.drop_duplicates(subset=["url"]).reset_index(drop=True)
            except Exception as e:
                self.logger.warning(f"기존 failed_urls.csv 읽기 실패, 새로 생성: {e}")
                combined = new_failed
        else:
            combined = new_failed
            
        combined.to_csv(failed_path, index=False, encoding="utf-8")
        self.logger.warning(f"수집 실패한 URL {len(combined)}건 저장됨: {failed_path}")
        self.failed_urls.clear()

    # ===== 기존 메서드들 =====
    
    def go_to_law_list(self):
        """법률 목록까지 이동"""
        try:
            self.driver.get(self.start_url)

            # "Văn bản quy phạm pháp luật" 클릭
            law_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(), "Văn bản quy phạm pháp luật")]')))
            law_button.click()

            # 기존 항목 수 파악
            initial_items = self.driver.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")
            initial_count = len(initial_items)

            # "Tìm kiếm" 클릭
            search_button = self.wait.until(EC.element_to_be_clickable((By.ID, "searchSubmit")))
            search_button.click()

            # 결과 로딩 대기
            self.wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")) != initial_count)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.listLaw > li")))

            return True

        except Exception as e:
            self.logger.critical(f"법률 목록 이동 실패: {e}")
            return False

    def extract_law_details(self, law_url):
        """법령 상세정보 추출"""
        self.driver.get(law_url)

        try:
            parsed_url = urlparse(law_url)
            q = {k.lower(): v for k, v in parse_qs(parsed_url.query).items()}
            item_id = (q.get('itemid', [None])[0] or '').strip()
            path_parts = parsed_url.path.strip('/').split('/')
            region_id = path_parts[0] if path_parts else None
        except Exception as e:
            self.logger.critical(f"URL에서 itemID 또는 regionID 가져오기 실패: {e}")
            return {}, [], []

        try:
            info = {
                "regionID": region_id,
                "itemID": item_id,
                "문서코드": "-", "법령명": "-", "문서유형": "-", "발급기관": "-",
                "유효상태": "-", "발행일": "-", "발효일": "-", "서명자 직위": "-",
                "서명자": "-", "유효범위": "-", "url": law_url,
            }

            download_link = []
            relations = []

            # "Thuộc tính" 탭 클릭
            try:
                tab_list = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.header ul li a")))
                for tab in tab_list:
                    if "Thuộc tính" in tab.text or "properties" in tab.get_attribute("innerHTML"):
                        tab.click()
                        break
                else:
                    self.logger.critical(f"Thuộc tính 탭을 찾을 수 없습니다: {law_url}")
                    return {}, [], []
            except Exception as e:
                self.logger.critical(f"tab_list를 불러오는데 실패: {law_url} | {e}")
                return {}, [], []

            # 속성 정보 추출
            self._extract_properties(info, law_url)
            
            # 다운로드 링크 추출
            download_link = self._extract_download_links(info, law_url)
            
            # 관계정보 추출
            relations = self._extract_relations(info, law_url)

            return info, relations, download_link

        except Exception as e:
            self.logger.critical(f"알 수 없는 오류 발생: {law_url} | {e}")
            return {}, [], []

    def _extract_properties(self, info: Dict, law_url: str):
        """속성 정보 추출"""
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.vbProperties table")))
            table = self.driver.find_element(By.CSS_SELECTOR, "div.vbProperties table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # 법령명
            try:
                info["법령명"] = table.find_element(By.CLASS_NAME, "title").text.strip()
            except:
                info["법령명"] = "-"

            for row in rows:
                tds = row.find_elements(By.TAG_NAME, "td")
                if not tds:
                    continue

                for i, td in enumerate(tds):
                    try:
                        if "label" in td.get_attribute("class"):
                            label = td.text.strip()

                            if "Số ký hiệu" in label:
                                info["문서코드"] = tds[i + 1].text.strip()
                            elif "Loại văn bản" in label:
                                info["문서유형"] = tds[i + 1].text.strip()
                            elif "Cơ quan ban hành/ Chức danh / Người ký" in label:
                                info["발급기관"] = tds[i + 1].text.strip()
                                info["서명자 직위"] = tds[i + 2].text.strip()
                                info["서명자"] = tds[i + 3].text.strip()
                            elif "Ngày ban hành" in label:
                                date_raw = tds[i + 1].text.strip()
                                try:
                                    info["발행일"] = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                                except:
                                    info["발행일"] = date_raw
                            elif "Ngày có hiệu lực" in label:
                                date_raw = tds[i + 1].text.strip()
                                try:
                                    info["발효일"] = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                                except:
                                    info["발효일"] = date_raw
                            elif "Phạm vi" in label:
                                try:
                                    info["유효범위"] = tds[i + 1].find_element(By.TAG_NAME, "li").text.strip()
                                except:
                                    info["유효범위"] = tds[i + 1].text.strip()

                    except Exception as e:
                        self.logger.error(f"row 처리 중 오류: {law_url} | {e}")
                        continue

            # 유효상태
            try:
                valid_status_raw = self.driver.find_element(By.CSS_SELECTOR, 
                    "div.vbInfo ul li:nth-child(1)").text.strip()
                info["유효상태"] = valid_status_raw.split(": ", 1)[-1].strip()
            except Exception as e:
                self.logger.info(f"유효상태 추출 중 오류: {law_url} | {e}")

        except Exception as e:
            self.logger.info(f"속성 테이블 처리 실패, 최소정보만 수집: {law_url} | {e}")
            # Toàn văn에서 최소정보 수집
            try:
                self.driver.back()
                div = self.driver.find_element(By.XPATH, "//div[contains(text(), 'Số:')]")
                info["문서코드"] = div.text.strip().replace("Số: ", "", 1)

                # 유효상태
                try:
                    valid_status_raw = self.driver.find_element(By.CSS_SELECTOR, 
                        "div.vbInfo ul li:nth-child(1)").text.strip()
                    info["유효상태"] = valid_status_raw.split(": ", 1)[-1].strip()
                except:
                    pass

                # 발효일
                try:
                    date_raw = self.driver.find_element(By.CSS_SELECTOR, 
                        "div.vbInfo ul li:nth-child(2)").text.strip()
                    date_without_label = date_raw.split(": ", 1)[-1].strip()
                    try:
                        info["발효일"] = datetime.strptime(date_without_label, "%d/%m/%Y").strftime("%Y-%m-%d")
                    except:
                        info["발효일"] = date_raw
                except:
                    pass
            except Exception as fallback_e:
                self.logger.error(f"최소정보 수집도 실패: {law_url} | {fallback_e}")

    def _extract_download_links(self, info: Dict, law_url: str) -> List[Dict]:
        """다운로드 링크 추출"""
        download_link = []
        try:
            download_div = self.driver.find_element(By.ID, "divShowDialogDownload")
            file_links = download_div.find_elements(By.CSS_SELECTOR, "ul.fileAttack a.show_hide")

            download_priority = {"doc": 1, "docx": 1, "pdf": 2, "zip": 3, "rar": 4}
            file_groups = {}

            for a_tag in file_links:
                href = a_tag.get_attribute("href")
                match = re.search(r"downloadfile\('.*?',\s*'(.*?)'\)", href)
                if match:
                    file_url = match.group(1).strip()
                    ext = file_url.split(".")[-1].lower()
                    if ext in download_priority:
                        priority = download_priority[ext]
                        if priority not in file_groups:
                            file_groups[priority] = []
                        full_url = urljoin("https://vbpl.vn", file_url)
                        file_groups[priority].append(full_url)

            # 가장 우선순위가 높은 그룹 선택
            for priority in sorted(file_groups.keys()):
                for url in file_groups[priority]:
                    download_link.append({
                        "regionID": info.get("regionID", "-"),
                        "itemID": info.get("itemID", "-"),
                        "문서코드": info.get("문서코드", "-"),
                        "다운로드 링크": url
                    })
                break

        except Exception as e:
            self.logger.info(f"다운로드 링크 추출 중 오류: {law_url} | {e}")
        
        return download_link

    def _extract_relations(self, info: Dict, law_url: str) -> List[Dict]:
        """관계정보 추출"""
        relations = []
        
        # "VB liên quan" 탭 클릭
        try:
            tab_list = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.header ul li a")))
            related_tab = next((tab for tab in tab_list if "VB liên quan" in tab.text), None)

            if not related_tab:
                self.logger.error(f"VB liên quan 탭을 찾을 수 없음: {law_url}")
                return []

            related_tab.click()

        except Exception as e:
            self.logger.error(f"VB liên quan 탭 클릭 실패: {law_url} | {e}")
            return []

        # 관계 테이블 로드 대기
        for i in range(1, 4):
            try:
                self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.vbLienQuan div.content table")))
                break
            except Exception as ex:
                self.logger.info(f"관계정보 테이블 로딩 재시도({i}/3): {ex}")
                time.sleep(2)
        else:
            self.logger.error(f"관계정보 테이블 로딩 실패: {law_url}")
            return []

        # 신규문서코드
        law_new_doc_code = info.get("문서코드", "-")
        new_doc_code = law_new_doc_code.replace(" ", "_") if law_new_doc_code else "-"

        # 관계유형 및 관계문서코드 수집
        try:
            tbody = self.driver.find_element(By.CSS_SELECTOR, 
                "div.vbLienQuan div.content table tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
        except Exception as e:
            self.logger.error(f"관계유형 테이블 요소 불러오기 실패: {law_url} | {e}")
            return []

        for row in rows:
            try:
                tds = row.find_elements(By.TAG_NAME, "td")
                if len(tds) != 2:  # "Nội dung đang cập nhật." 경우 무시
                    continue

                relation_type = tds[0].text.strip()

                try:
                    li_items = tds[1].find_elements(By.CSS_SELECTOR, "ul.listVB > li")
                except Exception as e:
                    self.logger.info(f"relation_itemID <li> 추출 실패: {law_url} | {e}")
                    continue

                for li in li_items:
                    try:
                        p_tag = li.find_element(By.CSS_SELECTOR, "div > p:first-of-type")
                        a_tag = p_tag.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")
                        relation_itemID = "-"

                        if href:
                            abs_url = urljoin("https://vbpl.vn", href)
                            p = urlparse(abs_url)
                            q = {k.lower(): v for k, v in parse_qs(p.query).items()}
                            item_id = (q.get("itemid", [None])[0] or "").strip()
                            if item_id:
                                relation_itemID = item_id
                            else:
                                m = re.search(r"[?&]itemid=(\d+)", abs_url, flags=re.I)
                                relation_itemID = m.group(1) if m else "-"

                        relations.append({
                            "regionID": info.get("regionID", "-"),
                            "itemID": info.get("itemID", "-"),
                            "신규문서코드": new_doc_code,
                            "relation_itemID": relation_itemID,
                            "관계유형": relation_type,
                        })
                    except Exception as e:
                        self.logger.info(f"relation_itemID 추출 실패: {law_url} | {e}")
                        relations.append({
                            "regionID": info.get("regionID", "-"),
                            "itemID": info.get("itemID", "-"),
                            "신규문서코드": new_doc_code,
                            "relation_itemID": "-",
                            "관계유형": relation_type,
                        })
            except Exception as e:
                self.logger.info(f"관계정보 행 처리 실패: {law_url} | {e}")
                continue

        return relations

    def get_all_law_urls(self, total_pages: int) -> List[str]:
        """법령 목록에서 전체 URL 목록 수집 (업데이터용)"""
        new_urls = []

        for page in range(1, total_pages + 1):
            self.logger.info(f"페이지 {page} URL 수집 중...")
            
            max_retry = 3
            for retry in range(max_retry):
                try:
                    self.go_to_law_list()
                    if page > 1:
                        self.wait.until(lambda d: d.execute_script(
                            "return typeof LoadPage === 'function';") == True)
                        self.driver.execute_script("LoadPage(arguments[0]);", page)
                    self.wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "ul.listLaw > li")))
                    time.sleep(1.5)

                    items = self.driver.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")
                    if not items:
                        raise Exception("문서 항목 비어 있음")

                    for item in items:
                        a_tag = item.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")
                        new_urls.append(href)

                    break

                except Exception as e:
                    self.logger.info(f"링크 추출 재시도 {retry+1}/{max_retry}: {e}")
                    time.sleep(5)
            else:
                self.logger.error(f"링크 추출 최종 실패. 페이지 {page} 스킵")
                continue

        self.logger.info(f"총 {len(new_urls)}개 URL 수집 완료")
        return new_urls