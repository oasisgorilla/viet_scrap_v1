# update/__init__.py  
from typing import Literal, TYPE_CHECKING
from log_util import setup_logger

if TYPE_CHECKING:
    from update.law_updater import LawUpdater

def make_law_updater(mode: Literal["central", "local"], scraper, **kwargs) -> "LawUpdater":
    """법령 업데이터 팩토리 함수"""
    from update.law_updater import LawUpdater
    
    # 모드별 로거 설정
    logger = setup_logger(
        f"{mode}_law_updater", 
        f"{mode}_law/log/{mode}_law_updater.log"
    )
    
    return LawUpdater(mode=mode, scraper=scraper, logger=logger)