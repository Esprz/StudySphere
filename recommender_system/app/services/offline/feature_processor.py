import logging

logger = logging.getLogger(__name__)


class FeatureProcessor:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def process_features(self):
        self.process_cf_user_item_interest_score()

    def process_cf_user_item_interest_score(self):
        with self.db_connection as conn:
            conn.execute(
                """
                SELECT refresh_user_item_interest('v1');
                """
            )
            conn.commit()
            logger.info("✅ Refreshed user-item interest scores")
