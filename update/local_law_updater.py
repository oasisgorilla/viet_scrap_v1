### update/local_law_updater.py ###
# 하위호환성을 위한 래퍼 - 기존 LocalLawUpdater 클래스
from update import make_law_updater
from scraper.local_law_scraper import LocalLawScraper
from log_util import setup_logger

class LocalLawUpdater:
    """
    하위호환성을 위한 래퍼 클래스
    실제 구현은 통합된 LawUpdater를 사용합니다.
    """
    def __init__(self, scraper: LocalLawScraper):
        self.scraper = scraper
        self.logger = setup_logger(__name__, "local_law/log/local_law_updater.log")
        self._updater = make_law_updater("local", scraper._scraper)

    def run(self):
        """기존 인터페이스 유지"""
        return self._updater.run()