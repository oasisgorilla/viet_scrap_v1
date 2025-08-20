from __future__ import annotations
from pathlib import Path
import pandas as pd
from typing import Iterable, List, Optional, Tuple, Dict, Any

# 프로젝트 로거 사용 (없어도 동작하도록 예외 처리)
try:
    from log_util import setup_logger
    LOGGER = setup_logger(__name__, "law_combined/log/merge_law_tables.log")
except Exception:
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
    LOGGER = logging.getLogger(__name__)

OUT_BASE = Path("law_combined")

# -------- 공통 유틸 --------
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_if_exists(path: Path) -> pd.DataFrame:
    try:
        if path.exists() and path.stat().st_size > 0:
            df = pd.read_excel(path)
            LOGGER.info(f"[read] {path} rows={len(df)}")
            return df
    except Exception as e:
        LOGGER.error(f"[read] failed: {path} | {e}")
    return pd.DataFrame()

def concat_and_drop_duplicates(dfs: List[pd.DataFrame], subset: List[str]) -> pd.DataFrame:
    if not dfs:
        return pd.DataFrame()
    df = pd.concat([d for d in dfs if not d.empty], ignore_index=True)
    if df.empty:
        return df
    # subset에 존재하는 컬럼만 사용 (없으면 무시)
    subset = [c for c in subset if c in df.columns]
    if subset:
        df = df.drop_duplicates(subset=subset, keep="last").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    return df

def reassign_pk(df: pd.DataFrame, pk_name: str = "id") -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if pk_name in df.columns:
        df = df.drop(columns=[pk_name])
    df.insert(0, pk_name, range(1, len(df) + 1))
    return df

def normalize_types(df: pd.DataFrame, to_str_cols: Iterable[str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for c in to_str_cols:
        if c in df.columns:
            df[c] = df[c].astype(str)
    return df

# -------- 메인 병합 로직 --------
def merge_info() -> Optional[Path]:
    """
    중앙/지방 '기본정보' 통합 → 베트남_법령_기본정보.xlsx
    중복 키: regionID + itemID
    """
    srcs = [
        Path("central_law/info/merged_result.xlsx"),
        Path("local_law/info/merged_result.xlsx"),
    ]
    dfs = [read_if_exists(p) for p in srcs]
    df = concat_and_drop_duplicates(dfs, subset=["regionID", "itemID"])
    if df.empty:
        LOGGER.warning("[info] 입력 데이터가 비었습니다.")
        return None

    # 타입 통일(잠재적 조인·후속처리 대비)
    df = normalize_types(df, ["regionID", "itemID"])

    out_dir = ensure_dir(OUT_BASE / "info")
    out_path = out_dir / "베트남_법령_기본정보.xlsx"
    df.to_excel(out_path, index=False)
    LOGGER.info(f"[info] 저장: {out_path} rows={len(df)}")
    return out_path

def merge_relation() -> Optional[Path]:
    """
    중앙/지방 '관계정보' 통합 → 베트남_법령_관계정보.xlsx
    중복 제거 없이 단순 병합
    """
    srcs = [
        Path("central_law/relation/merged_result.xlsx"),
        Path("local_law/relation/merged_result.xlsx"),
    ]
    dfs = [read_if_exists(p) for p in srcs]
    df = pd.concat([d for d in dfs if not d.empty], ignore_index=True) # 중복체크 하지 않음
    if df.empty:
        LOGGER.warning("[relation] 입력 데이터가 비었습니다.")
        return None

    # 타입 통일
    df = normalize_types(df, ["regionID", "itemID", "relation_itemID"])

    # id 재부여
    df = reassign_pk(df, "id")

    out_dir = ensure_dir(OUT_BASE / "relation")
    out_path = out_dir / "베트남_법령_관계정보.xlsx"
    df.to_excel(out_path, index=False)
    LOGGER.info(f"[relation] 저장: {out_path} rows={len(df)}")
    return out_path

def merge_download_link() -> Optional[Path]:
    """
    중앙/지방 '다운로드링크' 통합 → 베트남_법령_파일링크.xlsx
    중복 키: regionID, itemID, 다운로드 링크
    """
    srcs = [
        Path("central_law/download_link/merged_result.xlsx"),
        Path("local_law/download_link/merged_result.xlsx"),
    ]
    dfs = [read_if_exists(p) for p in srcs]

    # 단순 병합 후 중복 제거
    df = concat_and_drop_duplicates(dfs, subset=["regionID", "itemID", "다운로드 링크"])
    if df.empty:
        LOGGER.warning("[download_link] 입력 데이터가 비었습니다.")
        return None

    # 타입 통일
    df = normalize_types(df, ["regionID", "itemID", "다운로드 링크"])

    # id 재부여
    df = reassign_pk(df, "id")

    out_dir = ensure_dir(OUT_BASE / "download_link")
    out_path = out_dir / "베트남_법령_파일링크.xlsx"
    df.to_excel(out_path, index=False)
    LOGGER.info(f"[download_link] 저장: {out_path} rows={len(df)}")
    return out_path

def copy_directive() -> Optional[Path]:
    """
    행정지시문서 기본정보를 이름만 바꿔 최종 위치로 복사 저장
    """
    src = Path("directive/info/merged_result.xlsx")
    df = read_if_exists(src)
    if df.empty:
        LOGGER.warning("[directive] 입력 데이터가 비었습니다.")
        return None
    out_dir = ensure_dir(OUT_BASE / "directive")
    out_path = out_dir / "베트남_중앙정부_행정_지시_문서_기본정보.xlsx"
    df.to_excel(out_path, index=False)
    LOGGER.info(f"[directive] 저장: {out_path} rows={len(df)}")
    return out_path

def main():
    ensure_dir(OUT_BASE / "log")
    LOGGER.info("=== 법령/행정지시 최종 통합 시작 ===")
    paths = {
        "베트남_법령_기본정보": merge_info(),
        "베트남_법령_관계정보": merge_relation(),
        "베트남_법령_파일링크": merge_download_link(),
        "베트남_중앙정부_행정_지시_문서_기본정보": copy_directive(),
    }
    ok = [k for k, v in paths.items() if v is not None]
    miss = [k for k, v in paths.items() if v is None]
    LOGGER.info(f"[요약] 생성 완료: {ok} | 미생성: {miss}")
    print("[merge_law_tables] done")

if __name__ == "__main__":
    main()
