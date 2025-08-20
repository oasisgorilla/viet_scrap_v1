### scrap_manager.py ###
# 모든 스크래퍼의 실행을 담당하는 파일 (팩토리 함수 사용)
from scraper import make_law_scraper
from scraper.directive_scraper import DirectiveScraper
from merge_law_tables import main as merge_main

if __name__ == "__main__":
    # 중앙정부 법령정보 수집
    central_scraper = make_law_scraper("central")
    central_scraper.run()

    # 지방정부 법령정보 수집
    local_scraper = make_law_scraper("local")
    local_scraper.run()

    # 행정지시문서 수집
    directive_scraper = DirectiveScraper()
    directive_scraper.run()

    # 스크래핑 후 전체 병합
    merge_main()