import pandas as pd
from pathlib import Path

# 엑셀파일 병합 코드

# 행정지시문서 병합코드
def gov_merge_excel(file_dir):
    # 병합할 파일들이 위치한 디렉토리 경로
    input_dir = Path(file_dir)
    files = list(input_dir.glob("*.xlsx"))

    # 모든 파일을 읽어 DataFrame 리스트로 저장
    print("파일을 데이터프레임으로 저장 중")
    dfs = [pd.read_excel(f) for f in files]
    print("데이터프레임 저장 완료")

    # vertical concatenate
    print("파일 병합 중")
    combined = pd.concat(dfs, ignore_index=True)
    print("병합 완료")

    # 중복된 '문서명' 행 제거: 중복 중 가장 마지막 행을 유지
    print("중복된 행 제거 중")
    combined_no_dup = combined.drop_duplicates(subset=['문서코드', '문서유형', '문서명'], keep='last').reset_index(drop=True)
    print("중복된 행 제거 완료")

    # 결과 저장
    combined_no_dup.to_excel(f"./{file_dir}/merged_result.xlsx", index=False)
    print(f"{file_dir}에 병합완료")
    print(f"Merged {len(files)} files → final {len(combined_no_dup)} rows saved.")

# 정부 세부정보 병합코드
def info_merge_excel(file_dir):
    # 병합할 파일들이 위치한 디렉토리 경로
    input_dir = Path(file_dir)
    files = list(input_dir.glob("*.xlsx"))

    # 모든 파일을 읽어 DataFrame 리스트로 저장
    print("파일을 데이터프레임으로 저장 중")
    dfs = [pd.read_excel(f) for f in files]
    print("데이터프레임 저장 완료")

    # vertical concatenate
    print("파일 병합 중")
    combined = pd.concat(dfs, ignore_index=True)
    print("병합 완료")

    # 중복된 '문서명' 행 제거: 중복 중 가장 마지막 행을 유지
    print("중복된 행 제거 중")
    combined_no_dup = combined.drop_duplicates(subset=['문서코드', '법령명', '문서유형', '발급기관', '유효상태', '발행일', '발효일', '서명자 직위', '서명자', '유효범위'], keep='last').reset_index(drop=True)
    print("중복된 행 제거 완료")

    # 결과 저장
    combined_no_dup.to_excel(f"./{file_dir}/merged_result.xlsx", index=False)
    print(f"{file_dir}에 병합완료")
    print(f"Merged {len(files)} files → final {len(combined_no_dup)} rows saved.")

# 정부 관계문서 병합코드
def relation_merge_excel(file_dir):
    # 병합할 파일들이 위치한 디렉토리 경로
    input_dir = Path(file_dir)
    files = list(input_dir.glob("*.xlsx"))

    # 모든 파일을 읽어 DataFrame 리스트로 저장
    print("파일을 데이터프레임으로 저장 중")
    dfs = [pd.read_excel(f) for f in files]
    print("데이터프레임 저장 완료")

    # vertical concatenate
    print("파일 병합 중")
    combined = pd.concat(dfs, ignore_index=True)
    print("병합 완료")

    # 중복된 '문서명' 행 제거: 중복 중 가장 마지막 행을 유지
    print("중복된 행 제거 중")
    combined_no_dup = combined.drop_duplicates(subset=['신규문서코드', '관계문서코드'], keep='last').reset_index(drop=True)
    print("중복된 행 제거 완료")

    # 결과 저장
    combined_no_dup.to_excel(f"./{file_dir}/merged_result.xlsx", index=False)
    print(f"{file_dir}에 병합완료")
    print(f"Merged {len(files)} files → final {len(combined_no_dup)} rows saved.")

# 정부 다운로드링크 병합코드
def download_link_merge_excel(file_dir):
    # 병합할 파일들이 위치한 디렉토리 경로
    input_dir = Path(file_dir)
    files = list(input_dir.glob("*.xlsx"))

    # 모든 파일을 읽어 DataFrame 리스트로 저장
    print("파일을 데이터프레임으로 저장 중")
    dfs = [pd.read_excel(f) for f in files]
    print("데이터프레임 저장 완료")

    # vertical concatenate
    print("파일 병합 중")
    combined = pd.concat(dfs, ignore_index=True)
    print("병합 완료")

    # 중복된 '문서명' 행 제거: 중복 중 가장 마지막 행을 유지
    print("중복된 행 제거 중")
    combined_no_dup = combined.drop_duplicates(subset=['문서코드', '다운로드 링크'], keep='last').reset_index(drop=True)
    print("중복된 행 제거 완료")

    # 결과 저장
    combined_no_dup.to_excel(f"./{file_dir}/merged_result.xlsx", index=False)
    print(f"{file_dir}에 병합완료")
    print(f"Merged {len(files)} files → final {len(combined_no_dup)} rows saved.")

gov_info_dir = "./gov_info_outputs"

central_info_dir = "./central_info_outputs"
central_relation_dir = "./central_relation_outputs"
central_download_link_dir = "./central_download_link_outputs"

local_info_dir = "./local_info_outputs"
local_relation_dir = "./local_relation_outputs"
local_download_link_dir = "./local_download_link_outputs"


# 중앙문서 작업
# print("중앙정부문서 병합 시작")
# info_merge_excel(central_info_dir)

# print("중앙정부관계문서 병합 시작")
# relation_merge_excel(central_relation_dir)

# print("중앙정부다운로드링크 병합 시작")
# download_link_merge_excel(central_download_link_dir)

# 지방문서 작업
# print("지방정부문서 병합 시작")
# info_merge_excel(local_info_dir)

# print("지방정부관계문서 병합 시작")
# relation_merge_excel(local_relation_dir)

# print("지방정부다운로드링크 병합 시작")
# download_link_merge_excel(local_download_link_dir)

# 행정지시문서 작업
print("행정지시문서 작업시작")
gov_merge_excel(gov_info_dir)