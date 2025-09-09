import numpy as np
import pandas as pd
import faiss
import os
import pickle
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sklearn.metrics.pairwise import cosine_similarity
import implicit

from app.utils.database import get_db_session
from app.models.schemas import IndexMetadata

logger = logging.getLogger(__name__)

class IndexBuilder:
    """Responsible for building and updating various indices needed for recommendation system"""
    
    def __init__(self, index_path, db_connection_string=None):
        """
        Initialize index builder
        
        Args:
            index_path: Path to store FAISS indices
            db_connection_string: PostgreSQL database connection string
        """
        self.index_path = index_path
        self.db_connection_string = db_connection_string
        
        # Ensure index directory exists
        os.makedirs(index_path, exist_ok=True)
        
    def build_all_indices(self):
        """Build all required indices"""
        logger.info("Starting to build all indices")
        
        # Build content-based vector index
        self.build_content_vector_index()
        
        # Build collaborative filtering model
        self.build_collaborative_filtering_model()
        
        # Build user similarity index
        self.build_user_similarity_index()
        
        # Build trending items index
        self.build_trending_items_index()
        
        logger.info("All indices built successfully")
        
    def build_content_vector_index(self):
        """Build FAISS vector index based on content"""
        logger.info("Starting to build content vector index")
        
        # 1. Get content and features from database
        item_embeddings, item_ids = self._get_content_embeddings()
        
        # 2. Build FAISS index
        self._build_faiss_index(
            embeddings=item_embeddings,
            ids=item_ids,
            index_name="content_vector_index"
        )
        
        # 3. Store content vectors in PostgreSQL (optional)
        self._store_vectors_in_postgres(
            embeddings=item_embeddings, 
            ids=item_ids, 
            table_name="content_embeddings"
        )
        
        logger.info(f"Content vector index built with {len(item_ids)} items")
        
    def build_collaborative_filtering_model(self):
        """Build collaborative filtering model (using implicit library)"""
        logger.info("Starting to build collaborative filtering model")
        
        # 1. Get user-item interaction data from database
        interactions, user_ids, item_ids = self._get_user_item_interactions()
        
        # 2. Build model
        model = implicit.als.AlternatingLeastSquares(
            factors=64, 
            regularization=0.1,
            iterations=20
        )
        model.fit(interactions)
        
        # 3. Save model
        model_path = os.path.join(self.index_path, "cf_model.pkl")
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': model,
                'user_ids': user_ids,
                'item_ids': item_ids
            }, f)
        
        # 4. Store user and item factors in PostgreSQL
        self._store_cf_factors_in_postgres(model, user_ids, item_ids)
        
        logger.info("Collaborative filtering model built successfully")
        
    def build_user_similarity_index(self):
        """Build user similarity index"""
        logger.info("Starting to build user similarity index")
        
        # 1. Get user embedding vectors
        user_embeddings, user_ids = self._get_user_embeddings()
        
        # 2. Build FAISS index
        self._build_faiss_index(
            embeddings=user_embeddings,
            ids=user_ids,
            index_name="user_similarity_index"
        )
        
        # 3. Store in PostgreSQL
        self._store_vectors_in_postgres(
            embeddings=user_embeddings, 
            ids=user_ids, 
            table_name="user_embeddings"
        )
        
        logger.info(f"User similarity index built with {len(user_ids)} users")
        
    def build_trending_items_index(self):
        """Build trending content index"""
        logger.info("Starting to build trending items index")
        
        # 1. Get trending items from database
        trending_items = self._get_trending_items()
        
        # 2. Store to file
        trending_path = os.path.join(self.index_path, "trending_items.pkl")
        with open(trending_path, 'wb') as f:
            pickle.dump(trending_items, f)
        
        # 3. Store in PostgreSQL
        self._store_trending_items_in_postgres(trending_items)
        
        logger.info("Trending items index built successfully")
    
    def _build_faiss_index(self, embeddings, ids, index_name):
        """
        Build FAISS index
        
        Args:
            embeddings: Embedding vector array (numpy array)
            ids: Corresponding ID list
            index_name: Index name
        """
        # Ensure vectors are in correct format
        embeddings = np.ascontiguousarray(embeddings.astype('float32'))
        
        # Create index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)  # Using L2 distance
        
        # Add vectors to index
        index.add(embeddings)
        
        # Save index
        faiss.write_index(index, os.path.join(self.index_path, f"{index_name}.faiss"))
        
        # Save ID mapping
        with open(os.path.join(self.index_path, f"{index_name}_ids.pkl"), "wb") as f:
            pickle.dump(ids, f)
        
        # Record metadata
        metadata = {
            'name': index_name,
            'dimensions': dimension,
            'num_vectors': len(ids),
            'created_at': datetime.now().isoformat()
        }
        
        with open(os.path.join(self.index_path, f"{index_name}_metadata.json"), "w") as f:
            import json
            json.dump(metadata, f)
        
        # Store metadata in database
        self._store_index_metadata(metadata)
    
    def _store_index_metadata(self, metadata):
        """Store index metadata in database"""
        if not self.db_connection_string:
            return
            
        with get_db_session() as db:
            # Assuming an IndexMetadata model exists
            index_meta = IndexMetadata(
                name=metadata['name'],
                dimensions=metadata['dimensions'],
                num_vectors=metadata['num_vectors'],
                created_at=datetime.fromisoformat(metadata['created_at'])
            )
            db.add(index_meta)
            db.commit()
    
    def _store_vectors_in_postgres(self, embeddings, ids, table_name):
        """Store vectors in PostgreSQL"""
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Prepare data
        df = pd.DataFrame({
            'id': ids,
            'embedding': [vector.tolist() for vector in embeddings],
            'created_at': datetime.now()
        })
        
        # Store in database
        with engine.connect() as conn:
            # Ensure table exists
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id VARCHAR(255) PRIMARY KEY,
                    embedding FLOAT[],
                    created_at TIMESTAMP
                )
            """))
            
            # Empty table
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            
            # Batch insert data
            for _, row in df.iterrows():
                conn.execute(text(f"""
                    INSERT INTO {table_name} (id, embedding, created_at)
                    VALUES (:id, :embedding, :created_at)
                """), {
                    'id': row['id'],
                    'embedding': row['embedding'],
                    'created_at': row['created_at']
                })
    
    def _store_cf_factors_in_postgres(self, model, user_ids, item_ids):
        """Store collaborative filtering model's user and item factors in PostgreSQL"""
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Get user and item factors
        user_factors = model.user_factors
        item_factors = model.item_factors
        
        # Store user factors
        user_df = pd.DataFrame({
            'user_id': user_ids,
            'factors': [factors.tolist() for factors in user_factors],
            'updated_at': datetime.now()
        })
        
        # Store item factors
        item_df = pd.DataFrame({
            'item_id': item_ids,
            'factors': [factors.tolist() for factors in item_factors],
            'updated_at': datetime.now()
        })
        
        # Insert into database
        with engine.connect() as conn:
            # Create user factors table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_factors (
                    user_id VARCHAR(255) PRIMARY KEY,
                    factors FLOAT[],
                    updated_at TIMESTAMP
                )
            """))
            
            # Create item factors table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS item_factors (
                    item_id VARCHAR(255) PRIMARY KEY,
                    factors FLOAT[],
                    updated_at TIMESTAMP
                )
            """))
            
            # Empty tables
            conn.execute(text("TRUNCATE TABLE user_factors"))
            conn.execute(text("TRUNCATE TABLE item_factors"))
            
            # Insert user factors
            for _, row in user_df.iterrows():
                conn.execute(text("""
                    INSERT INTO user_factors (user_id, factors, updated_at)
                    VALUES (:user_id, :factors, :updated_at)
                """), {
                    'user_id': row['user_id'],
                    'factors': row['factors'],
                    'updated_at': row['updated_at']
                })
            
            # Insert item factors
            for _, row in item_df.iterrows():
                conn.execute(text("""
                    INSERT INTO item_factors (item_id, factors, updated_at)
                    VALUES (:item_id, :factors, :updated_at)
                """), {
                    'item_id': row['item_id'],
                    'factors': row['factors'],
                    'updated_at': row['updated_at']
                })
    
    def _store_trending_items_in_postgres(self, trending_items):
        """Store trending items in PostgreSQL"""
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Prepare data
        df = pd.DataFrame({
            'item_id': [item['id'] for item in trending_items],
            'score': [item['score'] for item in trending_items],
            'category': [item.get('category', 'general') for item in trending_items],
            'updated_at': datetime.now()
        })
        
        # Insert into database
        with engine.connect() as conn:
            # Create table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS trending_items (
                    item_id VARCHAR(255) PRIMARY KEY,
                    score FLOAT,
                    category VARCHAR(100),
                    updated_at TIMESTAMP
                )
            """))
            
            # Empty table
            conn.execute(text("TRUNCATE TABLE trending_items"))
            
            # Insert data
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO trending_items (item_id, score, category, updated_at)
                    VALUES (:item_id, :score, :category, :updated_at)
                """), {
                    'item_id': row['item_id'],
                    'score': row['score'],
                    'category': row['category'],
                    'updated_at': row['updated_at']
                })
    
    def _get_content_embeddings(self):
        """
        Get content embedding vectors from database
        
        Returns:
            embeddings: Embedding vector array
            ids: Corresponding ID list
        """
        # Logic to get content embedding vectors from database should be implemented here
        # Example:
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, embedding FROM content_features
                    WHERE embedding IS NOT NULL
                """))
                
                ids = []
                embeddings = []
                
                for row in result:
                    ids.append(row[0])
                    embeddings.append(np.array(row[1]))
                
                return np.array(embeddings), ids
        
        # If no connection string or query fails, return test data
        return np.random.random((100, 128)), [f"item_{i}" for i in range(100)]
    
    def _get_user_item_interactions(self):
        """
        Get user-item interaction data from database
        
        Returns:
            interactions: User-item interactions in sparse matrix format
            user_ids: User ID list
            item_ids: Item ID list
        """
        # Logic to get user-item interaction data from database should be implemented here
        # Example:
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT user_id, item_id, rating FROM user_item_interactions
                """))
                
                interactions = []
                user_ids_set = set()
                item_ids_set = set()
                
                for row in result:
                    user_id, item_id, rating = row
                    interactions.append((user_id, item_id, rating))
                    user_ids_set.add(user_id)
                    item_ids_set.add(item_id)
                
                # Convert to list and sort for consistency
                user_ids = sorted(list(user_ids_set))
                item_ids = sorted(list(item_ids_set))
                
                # Create mappings for user IDs and item IDs
                user_idx = {user_id: i for i, user_id in enumerate(user_ids)}
                item_idx = {item_id: i for i, item_id in enumerate(item_ids)}
                
                # Create sparse matrix
                from scipy.sparse import csr_matrix
                
                rows = [user_idx[user_id] for user_id, _, _ in interactions]
                cols = [item_idx[item_id] for _, item_id, _ in interactions]
                data = [rating for _, _, rating in interactions]
                
                interactions_matrix = csr_matrix(
                    (data, (rows, cols)),
                    shape=(len(user_ids), len(item_ids))
                )
                
                return interactions_matrix, user_ids, item_ids
        
        # If no connection string or query fails, return test data
        from scipy.sparse import random as sparse_random
        
        user_ids = [f"user_{i}" for i in range(100)]
        item_ids = [f"item_{i}" for i in range(200)]
        
        # Create a sparse random matrix
        interactions = sparse_random(100, 200, density=0.05)
        
        return interactions, user_ids, item_ids
    
    def _get_user_embeddings(self):
        """
        Get user embedding vectors from database
        
        Returns:
            embeddings: User embedding vector array
            user_ids: User ID list
        """
        # Logic to get user embedding vectors from database should be implemented here
        # Example:
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, embedding FROM user_features
                    WHERE embedding IS NOT NULL
                """))
                
                ids = []
                embeddings = []
                
                for row in result:
                    ids.append(row[0])
                    embeddings.append(np.array(row[1]))
                
                return np.array(embeddings), ids
        
        # If no connection string or query fails, return test data
        return np.random.random((100, 64)), [f"user_{i}" for i in range(100)]
    
    def _get_trending_items(self):
        """
        Get trending/popular content
        
        Returns:
            trending_items: List of trending items
        """
        # Logic to get trending content should be implemented here
        # Example:
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, title, views, likes, comments, 
                           created_at, category
                    FROM content_items
                    ORDER BY (views + likes * 2 + comments * 3) DESC
                    LIMIT 100
                """))
                
                trending_items = []
                
                for row in result:
                    id, title, views, likes, comments, created_at, category = row
                    score = views + likes * 2 + comments * 3
                    
                    trending_items.append({
                        'id': id,
                        'title': title,
                        'score': score,
                        'category': category,
                        'created_at': created_at.isoformat() if created_at else None
                    })
                
                return trending_items
        
        # If no connection string or query fails, return test data
        return [
            {'id': f"item_{i}", 'title': f"Trending Item {i}", 'score': 100 - i, 'category': 'general'}
            for i in range(100)
        ]