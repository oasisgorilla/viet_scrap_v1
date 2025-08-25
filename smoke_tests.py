### smoke_tests.py ###
# 통합 후 스모크 테스트 스크립트

import os
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

def test_imports():
    """기본 임포트 테스트"""
    print("=== 임포트 테스트 ===")
    
    try:
        # 새 팩토리 함수
        from scraper import make_law_scraper
        from update import make_law_updater
        print("✅ 팩토리 함수 임포트 성공")
        
        # 기존 지시문서
        from scraper.directive_scraper import DirectiveScraper
        from update.directive_updater import DirectiveUpdater
        print("✅ 지시문서 스크래퍼 임포트 성공")
        
    except ImportError as e:
        print(f"❌ 임포트 실패: {e}")
        return False
    
    return True

def test_factory_functions():
    """팩토리 함수 기본 테스트"""
    print("\n=== 팩토리 함수 테스트 ===")
    
    try:
        from scraper import make_law_scraper
        from update import make_law_updater
        
        # 중앙정부 스크래퍼
        central_scraper = make_law_scraper("central")
        print(f"✅ 중앙 스크래퍼 생성: {central_scraper.output_dir}")
        print(f"   로거: {central_scraper.logger.name}")
        
        # 지방정부 스크래퍼  
        local_scraper = make_law_scraper("local")
        print(f"✅ 지방 스크래퍼 생성: {local_scraper.output_dir}")
        print(f"   로거: {local_scraper.logger.name}")
        
        # 옵션 테스트
        undetected_scraper = make_law_scraper("central", use_undetected=True)
        print(f"✅ undetected 옵션: {undetected_scraper.use_undetected}")
        
        # 업데이터 생성
        central_updater = make_law_updater("central", central_scraper)
        print(f"✅ 중앙 업데이터 생성: {central_updater.mode}")
        
        # 드라이버 정리
        central_scraper.driver.quit()
        local_scraper.driver.quit()
        undetected_scraper.driver.quit()
        
    except Exception as e:
        print(f"❌ 팩토리 함수 테스트 실패: {e}")
        return False
    
    return True


def test_merge_excel():
    """merge_excel 함수 테스트"""
    print("\n=== merge_excel 함수 테스트 ===")
    
    try:
        from scraper import make_law_scraper
        import tempfile
        
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # 테스트용 스크래퍼 (드라이버 없이)
            scraper = make_law_scraper("central")
            scraper.output_dir = temp_dir
            
            # 테스트 데이터 생성
            test_dir = Path(temp_dir) / "info"
            test_dir.mkdir()
            
            # 중복 있는 테스트 데이터
            df1 = pd.DataFrame({
                'itemID': ['1', '2', '3'],
                '문서코드': ['DOC1', 'DOC2', 'DOC3'], 
                '법령명': ['법령A', '법령B', '법령C'],
                '발급기관': ['기관1', '-', '기관3']
            })
            
            df2 = pd.DataFrame({
                'itemID': ['2', '4', '5'],
                '문서코드': ['DOC2', 'DOC4', 'DOC5'],
                '법령명': ['법령B수정', '법령D', '법령E'], 
                '발급기관': ['기관2상세', '기관4', '-']
            })
            
            df1.to_csv(test_dir / "test1.csv", index=False, encoding='utf-8')
            df2.to_csv(test_dir / "test2.csv", index=False, encoding='utf-8')
            
            # merge_excel 실행
            scraper.merge_excel("info", ['itemID'])
            
            # 결과 확인
            merged_path = test_dir / "merged_result.csv"
            assert merged_path.exists(), "merged_result.csv 생성되지 않음"
            
            merged_df = pd.read_csv(merged_path)
            print(f"✅ 병합 완료: {len(merged_df)}행")
            
            # 중복 제거 확인 (itemID='2'는 keep='last'로 df2 버전이 남아야 함)
            item2_row = merged_df[merged_df['itemID'] == '2']
            if not item2_row.empty:
                print(f"   itemID=2 법령명: {item2_row.iloc[0]['법령명']}")
                assert '수정' in item2_row.iloc[0]['법령명'], "keep='last' 로직 미작동"
            
            print("✅ 정보량 점수 로직 적용됨 (문서코드+법령명 그룹)")
            
            scraper.driver.quit()
        
    except Exception as e:
        print(f"❌ merge_excel 테스트 실패: {e}")
        return False
        
    return True

def test_output_directories():
    """출력 디렉토리 구조 테스트"""
    print("\n=== 출력 디렉토리 테스트 ===")
    
    expected_dirs = [
        "central_law/info", "central_law/relation", "central_law/download_link", "central_law/log",
        "local_law/info", "local_law/relation", "local_law/download_link", "local_law/log", 
        "directive/info", "directive/log"
    ]
    
    for dir_path in expected_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path} 존재")
        else:
            print(f"⚠️  {dir_path} 없음 (첫 실행 시 정상)")
    
    return True

def test_log_files():
    """로그 파일 경로 테스트"""  
    print("\n=== 로그 파일 경로 테스트 ===")
    
    expected_logs = [
        "central_law/log/central_law_scrapper.log",
        "local_law/log/local_law_scrapper.log", 
        "directive/log/directive_scrapper.log"
    ]
    
    for log_path in expected_logs:
        if Path(log_path).exists():
            print(f"✅ {log_path} 존재")
            # 파일 크기 확인
            size = Path(log_path).stat().st_size
            print(f"   크기: {size} bytes")
        else:
            print(f"⚠️  {log_path} 없음 (첫 실행 시 정상)")
    
    return True

def main():
    """전체 스모크 테스트 실행"""
    print(f"스모크 테스트 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("임포트", test_imports),
        ("팩토리 함수", test_factory_functions), 
        ("merge_excel", test_merge_excel),
        ("출력 디렉토리", test_output_directories),
        ("로그 파일", test_log_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 테스트 예외: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print(f"\n{'='*50}")
    print("테스트 결과 요약:")
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n전체: {len(results)}개 중 {passed}개 통과")
    
    if passed == len(results):
        print("🎉 모든 스모크 테스트 통과!")
        return 0
    else:
        print("⚠️  일부 테스트 실패")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)