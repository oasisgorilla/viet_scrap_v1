# scraper/__init__.py
from typing import Literal, TYPE_CHECKING
from log_util import setup_logger

if TYPE_CHECKING:
    from scraper.law_scraper import LawScraper

def make_law_scraper(mode: Literal["central", "local"], **kwargs) -> "LawScraper":
    """법령 스크래퍼 팩토리 함수"""
    from scraper.law_scraper import LawScraper
    
    # 모드별 로거 설정
    logger = setup_logger(
        f"{mode}_law_scraper", 
        f"{mode}_law/log/{mode}_law_scrapper.log"
    )
    
    # 옵션 추출
    use_undetected = kwargs.get('use_undetected', False)
    
    return LawScraper(mode=mode, logger=logger, use_undetected=use_undetected)