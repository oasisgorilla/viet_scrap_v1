import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
from math import ceil
import time
from pathlib import Path
import undetected_chromedriver as uc

# 법률 목록까지 이동하는 함수
def go_to_law_list(driver, url, error_logs):
    wait = WebDriverWait(driver, 10)

    try:
        # 1단계 - 사이트 접속
        driver.get(url)

        # 2단계 - "Văn bản quy phạm pháp luật" 클릭
        try:
            law_button = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//a[contains(text(), "Văn bản quy phạm pháp luật")]')
            ))
            law_button.click()
        except Exception as e:
            msg = f"#2 [go_to_law_list] 'Văn bản quy phạm pháp luật' 버튼 클릭 실패: {url} | {str(e)}"
            print(msg)
            error_logs.append(msg)
            return False

        # <div id="grid_vanban">의 기존 항목 수 파악
        try:
            initial_items = driver.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")
            initial_count = len(initial_items)
        except Exception as e:
            msg = f"#3 [go_to_law_list] 최초 화면 목록 수 파악 실패: {url} | {str(e)}"
            print(msg)
            error_logs.append(msg)
            return False

        # 3단계 - "Tìm kiếm" 클릭
        try:
            search_button = wait.until(EC.element_to_be_clickable((By.ID, "searchSubmit")))
            search_button.click()
        except Exception as e:
            msg = f"#4 [go_to_law_list] 'Tìm kiếm' 버튼 클릭 실패: {url} | {str(e)}"
            print(msg)
            error_logs.append(msg)
            return False

        # 4단계 - 항목 수가 바뀔 때까지 대기
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "ul.listLaw > li")) != initial_count
            )
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.listLaw > li")))
        except Exception as e:
            msg = f"#5 [go_to_law_list] 'Tìm kiếm' 결과 로딩 실패: {url} | {str(e)}"
            print(msg)
            error_logs.append(msg)
            return False

        return True  # 정상 완료

    except Exception as e:
        msg = f"#6 [go_to_law_list] 알 수 없는 예외 발생: {url} | {str(e)}"
        print(msg)
        error_logs.append(msg)
        return False

# HTTPConnectionPool(host='localhost', port=59669): Read timed out. 재시도 로직
def safe_go_to_law_list(driver, url, error_logs, retries=4, delay=60):
    for attempt in range(1, retries + 1):
        try:
            success = go_to_law_list(driver, url, error_logs)
            if success:
                return True
        except Exception as e:
            msg = f"#31 [{attempt}/{retries}] go_to_law_list 재시도 중 오류 발생: {url} | {str(e)}"
            print(msg)
            error_logs.append(msg)

        # 마지막 전 시도에는 긴 대기
        if retries >= 2 and attempt == retries - 1:
            wait_time = 1800
        else:
            wait_time = delay
        time.sleep(wait_time)

    # 모든 시도 실패
    msg = f"#32 [safe_go_to_law_list] 목록 진입 최종 실패: {url}"
    print(msg)
    error_logs.append(msg)
    return False


options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--headless")
driver = uc.Chrome(options=options)

local_law_counts = []
total_local_law_count = 0
error_logs = []

try:
    # 처음 페이지에서 숨겨진 지역 목록 추출
    driver.get("https://vbpl.vn/TW/Pages/home.aspx")
    wait = WebDriverWait(driver, 10)
    time.sleep(2)

    region_links = []
    # 리스트가 숨겨져 있더라도 DOM에는 존재 → visibility 무시하고 수집
    li_tags = driver.find_elements(By.CSS_SELECTOR, "div.list-diaphuong div.container tr:nth-child(2) li")
    base_url = "https://vbpl.vn"
    for li in li_tags:
        try:
            a_tag = li.find_element(By.TAG_NAME, "a")
            href = a_tag.get_attribute("href")
            full_url = urljoin(base_url, href)

            parsed = urlparse(full_url)
            region_code = parsed.path.strip("/")  # 예: '/danang' → 'danang'

            # 'tw'이거나 빈 문자열인 경우는 스킵
            if not region_code or region_code.lower() == "tw":
                continue

            region_links.append((region_code, full_url))
        except:
            print(f"#1 {li.text}지방 <li>태그 데이터 추출 실패")
            continue
    for i in range(0, len(region_links)):
        current_region = region_links[i][0]
        current_link = region_links[i][1]
        # 목록으로 이동
        if not safe_go_to_law_list(driver, current_link, error_logs):
            print("#33 문서목록으로 이동 실패")
        try:
            # 전체 법령 항목 수와 페이지 수 구하기
            total_docs_text = driver.find_element(By.CSS_SELECTOR, "div#grid_vanban div.box-container div#tabVB_lv1 div.header ul li a.selected b").text
            total_docs = int(total_docs_text.replace(".", "").replace(",", "").strip())
            total_pages = ceil(total_docs / 30)
            print(f"[{current_region}]총 문서 수: {total_docs}, 총 페이지 수: {total_pages}")
            local_law_counts.append(total_docs)
            total_local_law_count += total_docs
        except Exception as e:
            print(f"#7 [{current_region}] 문서 수 불러오기 중 오류 error log: {e}")

    print(local_law_counts)
    print(total_local_law_count)
finally:
    driver.quit()