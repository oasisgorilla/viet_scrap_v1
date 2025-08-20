### update/central_law_updater.py ###
# 하위호환성을 위한 래퍼 - 기존 CentralLawUpdater 클래스
from update import make_law_updater
from scraper.central_law_scraper import CentralLawScraper
from log_util import setup_logger

class CentralLawUpdater:
    """
    하위호환성을 위한 래퍼 클래스
    실제 구현은 통합된 LawUpdater를 사용합니다.
    """
    def __init__(self, scraper: CentralLawScraper):
        self.scraper = scraper
        self.logger = setup_logger(__name__, "central_law/log/central_law_updater.log")
        self._updater = make_law_updater("central", scraper._scraper)

    def run(self):
        """기존 인터페이스 유지"""
        return self._updater.run()