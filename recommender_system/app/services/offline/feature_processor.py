import numpy as np
import pandas as pd
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

from app.utils.database import get_db_session

logger = logging.getLogger(__name__)

class FeatureProcessor:
    """Responsible for processing and generating features needed for the recommendation system"""
    
    def __init__(self, db_connection_string=None):
        """
        Initialize feature processor
        
        Args:
            db_connection_string: PostgreSQL database connection string
        """
        self.db_connection_string = db_connection_string
    
    def process_all_features(self):
        """Process all features"""
        logger.info("Starting to process all features")
        
        # Process content features
        self.process_content_features()
        
        # Process user features
        self.process_user_features()
        
        # Process interaction features
        self.process_interaction_features()
        
        logger.info("All feature processing completed")
    
    def process_content_features(self):
        """Process content features"""
        logger.info("Starting to process content features")
        
        # 1. Get content data
        content_data = self._get_content_data()
        
        # 2. Extract text features
        embeddings = self._extract_text_features(content_data)
        
        # 3. Store features to database
        self._store_content_features(content_data['id'], embeddings)
        
        logger.info(f"Content feature processing complete, total: {len(content_data)} items")
    
    def process_user_features(self):
        """Process user features"""
        logger.info("Starting to process user features")
        
        # 1. Get user data
        user_data = self._get_user_data()
        
        # 2. Extract user features
        embeddings = self._extract_user_features(user_data)
        
        # 3. Store features to database
        self._store_user_features(user_data['id'], embeddings)
        
        logger.info(f"User feature processing complete, total: {len(user_data)} users")
    
    def process_interaction_features(self):
        """Process interaction features"""
        logger.info("Starting to process interaction features")
        
        # 1. Get interaction data
        interactions = self._get_interaction_data()
        
        # 2. Calculate interaction statistical features
        interaction_features = self._compute_interaction_features(interactions)
        
        # 3. Store features to database
        self._store_interaction_features(interaction_features)
        
        logger.info("Interaction feature processing complete")
    
    def _get_content_data(self):
        """
        Get content data from database
        
        Returns:
            DataFrame: DataFrame containing ID, title, description, etc.
        """
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, title, description, content, category, created_at
                    FROM content_items
                """))
                
                return pd.DataFrame(result.fetchall(), 
                                   columns=['id', 'title', 'description', 'content', 'category', 'created_at'])
        
        # If no connection string or query fails, return test data
        return pd.DataFrame({
            'id': [f"item_{i}" for i in range(100)],
            'title': [f"Title {i}" for i in range(100)],
            'description': [f"Description for item {i}" for i in range(100)],
            'content': [f"Content text for item {i} with more words" for i in range(100)],
            'category': [f"category_{i%5}" for i in range(100)],
            'created_at': [datetime.now() for _ in range(100)]
        })
    
    def _extract_text_features(self, content_data):
        """
        Extract features from content text
        
        Args:
            content_data: DataFrame containing text content
            
        Returns:
            Feature vector array
        """
        # Combine title, description, and content
        text_data = content_data['title'] + " " + content_data['description'] + " " + content_data['content']
        
        # Use TF-IDF to extract features
        vectorizer = TfidfVectorizer(max_features=1000)
        tfidf_features = vectorizer.fit_transform(text_data)
        
        # Dimensionality reduction to get more compact feature representation
        svd = TruncatedSVD(n_components=128)
        embeddings = svd.fit_transform(tfidf_features)
        
        return embeddings
    
    def _store_content_features(self, ids, embeddings):
        """
        Store content features to database
        
        Args:
            ids: List of content IDs
            embeddings: Feature vector array
        """
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Prepare data
        df = pd.DataFrame({
            'id': ids,
            'embedding': [vector.tolist() for vector in embeddings],
            'updated_at': datetime.now()
        })
        
        # Store in database
        with engine.connect() as conn:
            # Ensure table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS content_features (
                    id VARCHAR(255) PRIMARY KEY,
                    embedding FLOAT[],
                    updated_at TIMESTAMP
                )
            """))
            
            # Insert or update data
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO content_features (id, embedding, updated_at)
                    VALUES (:id, :embedding, :updated_at)
                    ON CONFLICT (id) DO UPDATE 
                    SET embedding = EXCLUDED.embedding, 
                        updated_at = EXCLUDED.updated_at
                """), {
                    'id': row['id'],
                    'embedding': row['embedding'],
                    'updated_at': row['updated_at']
                })
    
    def _get_user_data(self):
        """
        Get user data from database
        
        Returns:
            DataFrame: DataFrame containing user information
        """
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, profile_data, preferences, registration_date
                    FROM users
                """))
                
                return pd.DataFrame(result.fetchall(), 
                                   columns=['id', 'profile_data', 'preferences', 'registration_date'])
        
        # If no connection string or query fails, return test data
        return pd.DataFrame({
            'id': [f"user_{i}" for i in range(100)],
            'profile_data': [{'age': 20+i%30, 'gender': 'M' if i%2 == 0 else 'F'} for i in range(100)],
            'preferences': [{'topics': [f'topic_{j}' for j in range(i%5, i%5+3)]} for i in range(100)],
            'registration_date': [datetime.now() for _ in range(100)]
        })
    
    def _extract_user_features(self, user_data):
        """
        Extract features from user data
        
        Args:
            user_data: DataFrame containing user information
            
        Returns:
            Feature vector array
        """
        # In a real application, meaningful features should be extracted based on user attributes and behaviors
        # This is just a simple example creating random features
        return np.random.random((len(user_data), 64))
    
    def _store_user_features(self, ids, embeddings):
        """
        Store user features to database
        
        Args:
            ids: List of user IDs
            embeddings: Feature vector array
        """
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Prepare data
        df = pd.DataFrame({
            'id': ids,
            'embedding': [vector.tolist() for vector in embeddings],
            'updated_at': datetime.now()
        })
        
        # Store in database
        with engine.connect() as conn:
            # Ensure table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_features (
                    id VARCHAR(255) PRIMARY KEY,
                    embedding FLOAT[],
                    updated_at TIMESTAMP
                )
            """))
            
            # Insert or update data
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT INTO user_features (id, embedding, updated_at)
                    VALUES (:id, :embedding, :updated_at)
                    ON CONFLICT (id) DO UPDATE 
                    SET embedding = EXCLUDED.embedding, 
                        updated_at = EXCLUDED.updated_at
                """), {
                    'id': row['id'],
                    'embedding': row['embedding'],
                    'updated_at': row['updated_at']
                })
    
    def _get_interaction_data(self):
        """
        Get interaction data from database
        
        Returns:
            DataFrame: DataFrame containing user-item interactions
        """
        if self.db_connection_string:
            engine = create_engine(self.db_connection_string)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT user_id, item_id, interaction_type, value, timestamp
                    FROM interactions
                """))
                
                return pd.DataFrame(result.fetchall(), 
                                   columns=['user_id', 'item_id', 'interaction_type', 'value', 'timestamp'])
        
        # If no connection string or query fails, return test data
        return pd.DataFrame({
            'user_id': [f"user_{i%100}" for i in range(1000)],
            'item_id': [f"item_{i%200}" for i in range(1000)],
            'interaction_type': [['view', 'like', 'share', 'comment'][i%4] for i in range(1000)],
            'value': [1 if i%4 > 0 else 0 for i in range(1000)],
            'timestamp': [datetime.now() for _ in range(1000)]
        })
    
    def _compute_interaction_features(self, interactions):
        """
        Calculate interaction statistical features
        
        Args:
            interactions: Interaction data DataFrame
            
        Returns:
            DataFrame containing interaction statistical features
        """
        # Calculate user-item interaction matrix
        user_item_matrix = interactions.pivot_table(
            index='user_id', 
            columns='item_id',
            values='value',
            aggfunc='sum'
        ).fillna(0)
        
        # Calculate user activity
        user_activity = interactions.groupby('user_id').size().reset_index(name='activity')
        
        # Calculate item popularity
        item_popularity = interactions.groupby('item_id').size().reset_index(name='popularity')
        
        return {
            'user_activity': user_activity,
            'item_popularity': item_popularity
        }
    
    def _store_interaction_features(self, features):
        """
        Store interaction features to database
        
        Args:
            features: Interaction features dictionary
        """
        if not self.db_connection_string:
            return
            
        engine = create_engine(self.db_connection_string)
        
        # Store user activity
        user_activity = features['user_activity']
        user_activity['updated_at'] = datetime.now()
        
        # Store item popularity
        item_popularity = features['item_popularity']
        item_popularity['updated_at'] = datetime.now()
        
        with engine.connect() as conn:
            # Create user activity table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id VARCHAR(255) PRIMARY KEY,
                    activity INT,
                    updated_at TIMESTAMP
                )
            """))
            
            # Create item popularity table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS item_popularity (
                    item_id VARCHAR(255) PRIMARY KEY,
                    popularity INT,
                    updated_at TIMESTAMP
                )
            """))
            
            # Insert user activity
            for _, row in user_activity.iterrows():
                conn.execute(text("""
                    INSERT INTO user_activity (user_id, activity, updated_at)
                    VALUES (:user_id, :activity, :updated_at)
                    ON CONFLICT (user_id) DO UPDATE 
                    SET activity = EXCLUDED.activity, 
                        updated_at = EXCLUDED.updated_at
                """), {
                    'user_id': row['user_id'],
                    'activity': row['activity'],
                    'updated_at': row['updated_at']
                })
            
            # Insert item popularity
            for _, row in item_popularity.iterrows():
                conn.execute(text("""
                    INSERT INTO item_popularity (item_id, popularity, updated_at)
                    VALUES (:item_id, :popularity, :updated_at)
                    ON CONFLICT (item_id) DO UPDATE 
                    SET popularity = EXCLUDED.popularity, 
                        updated_at = EXCLUDED.updated_at
                """), {
                    'item_id': row['item_id'],
                    'popularity': row['popularity'],
                    'updated_at': row['updated_at']
                })