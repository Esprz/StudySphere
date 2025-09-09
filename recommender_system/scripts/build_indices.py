#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import time
from datetime import datetime
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.offline.feature_processor import FeatureProcessor
from app.services.offline.index_builder import IndexBuilder
from app.utils.database import get_db_connection_string

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"build_indices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="构建推荐系统索引")
    parser.add_argument("--index-path", type=str, default="data/indices",
                        help="索引存储路径")
    parser.add_argument("--features-only", action="store_true",
                        help="只处理特征，不构建索引")
    parser.add_argument("--indices-only", action="store_true",
                        help="只构建索引，不处理特征")
    
    args = parser.parse_args()
    
    # 确保索引目录存在
    os.makedirs(args.index_path, exist_ok=True)
    
    # 获取数据库连接字符串
    db_connection_string = get_db_connection_string()
    
    start_time = time.time()
    
    try:
        # 处理特征
        if not args.indices_only:
            logger.info("开始处理特征")
            feature_processor = FeatureProcessor(db_connection_string)
            feature_processor.process_all_features()
            logger.info("特征处理完成")
        
        # 构建索引
        if not args.features_only:
            logger.info("开始构建索引")
            index_builder = IndexBuilder(args.index_path, db_connection_string)
            index_builder.build_all_indices()
            logger.info("索引构建完成")
        
        elapsed_time = time.time() - start_time
        logger.info(f"处理完成，耗时 {elapsed_time:.2f} 秒")
        
    except Exception as e:
        logger.error(f"处理过程中出错: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()