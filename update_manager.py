### update_manager.py ###
# 모든 업데이터의 실행을 담당하는 파일 (팩토리 함수 사용)
from scraper import make_law_scraper
from update import make_law_updater
from scraper.directive_scraper import DirectiveScraper
from update.directive_updater import DirectiveUpdater
from merge_law_tables import main as merge_main

if __name__ == "__main__":
    # 중앙정부 법령 업데이트
    central_scraper = make_law_scraper("central")
    central_updater = make_law_updater("central", central_scraper)
    central_updater.run()

    # 지방정부 법령 업데이트
    local_scraper = make_law_scraper("local")
    local_updater = make_law_updater("local", local_scraper)
    local_updater.run()

    # 행정지시문서 업데이트
    directive_scraper = DirectiveScraper()
    directive_updater = DirectiveUpdater(directive_scraper)
    directive_updater.run()

    # 업데이트 후 전체 병합
    merge_main()