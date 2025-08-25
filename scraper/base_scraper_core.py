### scraper/base_scraper_core.py ###
# 드라이버 초기화, 페이지 이동, 병합 등의 공통기능을 다룹니다.

import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs, urljoin
import re
import time
from pathlib import Path
from math import ceil
import logging
import undetected_chromedriver as uc

# 한국시간 정의(UTC+9)
KST = timezone(timedelta(hours=9))

class BaseScraper:
    """공통 스크래퍼 베이스 클래스 - 드라이버 초기화, 병합, 재시도 로직 등"""
    
    def __init__(self, base_url, start_url, output_dir, wait_time, docs_per_page, 
                 logger=None, use_undetected=False):
        self.base_url = base_url
        self.start_url = start_url
        self.docs_per_page = docs_per_page
        self.output_dir = output_dir
        self.wait_time = wait_time
        self.use_undetected = use_undetected
        self.driver, self.wait = self._init_driver()
        self.logger = logger or logging.getLogger(__name__)
        self.failed_urls = []
        os.makedirs(output_dir, exist_ok=True)

    def _init_driver(self):
        """드라이버 초기화 - 공통 옵션 적용"""
        if self.use_undetected:
            options = uc.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = uc.Chrome(options=options)
        else:
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=options)
        
        wait = WebDriverWait(driver, self.wait_time)
        return driver, wait

    def merge_excel(self, subfolder: str, subset_keys: list[str]):
        """엑셀 파일 병합 - 법령용 정보량 점수 로직 포함"""
        input_dir = Path(self.output_dir) / subfolder
        files = [f for f in input_dir.glob("*.csv")
                if f.name not in {"merged_result.csv", "updated_result.csv"}]
        if not files:
            self.logger.info(f"[merge_excel] 대상 파일 없음: {input_dir}")
            return

        dfs = []
        for f in files:
            try:
                if f.stat().st_size > 0:
                    dfs.append(pd.read_csv(f))
            except Exception as e:
                self.logger.warning(f"[merge_excel] 읽기 실패: {f} | {e}")
        if not dfs:
            self.logger.info(f"[merge_excel] 읽을 수 있는 엑셀 없음: {input_dir}")
            return

        combined = pd.concat(dfs, ignore_index=True)

        # 1단계: 전달된 키로 1차 중복 제거
        if subset_keys:
            combined = combined.drop_duplicates(subset=subset_keys, keep='last').reset_index(drop=True)
        else:
            combined = combined.reset_index(drop=True)

        # 2단계: 법령(info) 전용 - 문서코드+법령명 그룹에서 '정보가 많은' 행을 선택
        if subfolder == "info" and {"문서코드", "법령명"}.issubset(combined.columns):
            def _norm(s):
                return (s.astype(str)
                        .str.strip()
                        .str.replace(r"\s+", " ", regex=True)
                        .str.lower()
                        .replace({"-": pd.NA, "": pd.NA, "none": pd.NA}))

            # 그룹 키(정규화)
            combined["_code_norm"]  = _norm(combined["문서코드"])
            combined["_title_norm"] = _norm(combined["법령명"])
            mask = combined["_code_norm"].notna() & combined["_title_norm"].notna()

            # '정보량 점수' 계산: 값이 채워진 컬럼 수 + 가중치
            filled_cols = [
                "문서코드","법령명","문서유형","발급기관","유효상태",
                "발행일","발효일","서명자 직위","서명자","유효범위",
                "itemID","regionID","url"
            ]
            def _is_filled(col: pd.Series) -> pd.Series:
                s = col.astype(str).str.strip().str.lower()
                return (~s.isin({"", "-", "none"})).astype(int)

            # 기본 점수: 채워진 컬럼 수
            filled_df = combined.reindex(columns=filled_cols, fill_value=pd.NA)
            filled_mask = filled_df.apply(_is_filled, axis=0)
            base_score = filled_mask.sum(axis=1)

            # 중요 필드 가중치
            bonus = (
                _is_filled(combined.get("발행일", pd.Series(index=combined.index))) +
                _is_filled(combined.get("발효일", pd.Series(index=combined.index))) +
                _is_filled(combined.get("유효상태", pd.Series(index=combined.index))) +
                _is_filled(combined.get("발급기관", pd.Series(index=combined.index)))
            )

            # 길이 힌트
            len_hint = (
                combined.get("법령명", "").astype(str).str.len().fillna(0) +
                combined.get("발급기관", "").astype(str).str.len().fillna(0)
            )

            combined["_score"] = base_score + bonus
            combined["_len_hint"] = len_hint

            # 그룹 내에서 점수 기준 정렬 후 최고점 선택
            kept = combined.loc[mask].assign(_idx=combined.index)
            kept = kept.sort_values(
                by=["_code_norm","_title_norm","_score","_len_hint","_idx"],
                ascending=[True, True, False, False, False]
            ).drop_duplicates(subset=["_code_norm","_title_norm"], keep="first")

            rest = combined.loc[~mask]
            combined = pd.concat([kept, rest], ignore_index=True)

            # 임시 컬럼 제거
            combined = combined.drop(columns=[c for c in ["_code_norm","_title_norm","_score","_len_hint","_idx"]
                                            if c in combined.columns])

        # 저장
        out_path = input_dir / "merged_result.csv"
        combined.to_csv(out_path, index=False, encoding='utf-8')
        self.logger.info(f"[merge_excel] 저장 완료: {out_path} (rows={len(combined)})")

    def safe_go_to(self, func, *args, retries=4, delay=60):
        """공통 재시도 로직"""
        for attempt in range(1, retries + 1):
            try:
                result = func(*args)
                if result:
                    return True
                else:
                    msg = f"[{attempt}/{retries}] 함수 실행 실패 (False 반환)"
            except Exception as e:
                msg = f"[{attempt}/{retries}] 함수 실행 중 예외: {e}"
            
            self.logger.info(msg)
            
            if retries >= 2 and attempt == retries - 1:
                delay = 1800  # 마지막 전 시도는 30분 대기
            
            time.sleep(delay)
        
        self.logger.critical(f"[safe_go_to] 최종 실행 실패")
        return False

    def safe_extract(self, func, url, *args, retries=4, delay=60):
        """공통 추출 재시도 로직"""
        for attempt in range(1, retries + 1):
            try:
                result = func(url, *args)
                if result:
                    return result
                else:
                    msg = f"[{attempt}/{retries}] 추출 실패 (빈 결과): {url}"
            except Exception as e:
                if retries >= 2 and attempt == retries - 1:
                    delay = 1800
                msg = f"[{attempt}/{retries}] 추출 중 예외: {url} | {e}"
            
            self.logger.info(msg)
            time.sleep(delay)
        
        self.logger.critical(f"[safe_extract] 최종 추출 실패: {url}")
        self.failed_urls.append(url)
        return {} if func.__name__.endswith('_details') else []