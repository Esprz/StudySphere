from services.offline.feature_processor import FeatureProcessor
from services.offline.index_builder import IndexBuilder
from app.utils.postgres_store import PostgresStore


def main():
    postgres_store = PostgresStore()
    db_connection = postgres_store.get_session()
    feature_processor = FeatureProcessor(db_connection)
    feature_processor.process_features()
    index_builder = IndexBuilder(db_connection)
    index_builder.build_indices()


if __name__ == "__main__":
    main()
