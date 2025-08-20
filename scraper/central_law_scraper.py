### scraper/central_law_scraper.py ###
# 하위호환성을 위한 래퍼 - 기존 CentralLawScraper 클래스
from scraper import make_law_scraper
from log_util import setup_logger

class CentralLawScraper:
    """
    하위호환성을 위한 래퍼 클래스
    실제 구현은 통합된 LawScraper를 사용합니다.
    """
    def __init__(self):
        # 기존과 동일한 로거 경로 유지
        self.logger = setup_logger(__name__, "central_law/log/central_law_scrapper.log")
        self._scraper = make_law_scraper("central")
        
        # 기존 속성들을 래핑
        self.output_dir = self._scraper.output_dir
        self.driver = self._scraper.driver
        self.wait = self._scraper.wait
        self.failed_urls = self._scraper.failed_urls
        self.info_results = self._scraper.info_results
        self.relations_results = self._scraper.relations_results
        self.download_link_results = self._scraper.download_link_results

    def run(self):
        """기존 인터페이스 유지"""
        return self._scraper.run()
    
    def get_all_law_urls(self, total_pages):
        """기존 인터페이스 유지"""
        return self._scraper.get_all_law_urls(total_pages)
    
    def safe_extract_law_details(self, url, *args, **kwargs):
        """기존 인터페이스 유지"""
        return self._scraper.safe_extract(self._scraper.extract_law_details, url)
    
    def merge_excel(self, subfolder, subset_keys):
        """기존 인터페이스 유지"""
        return self._scraper.merge_excel(subfolder, subset_keys)