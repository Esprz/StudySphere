import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

class LearningToRankRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.post_features = None
        
    def fetch_and_prepare_data(self):
        # Get interaction data
        query = """
        SELECT 
            l.user_id, l.post_id, 
            1 as interaction_value,
            p.created_at,
            u.created_at as user_created_at
        FROM like l
        JOIN post p ON l.post_id = p.post_id
        JOIN "user" u ON l.user_id = u.user_id
        UNION ALL
        SELECT 
            s.user_id, s.post_id, 
            1 as interaction_value,
            p.created_at,
            u.created_at as user_created_at
        FROM save s
        JOIN post p ON s.post_id = p.post_id
        JOIN "user" u ON s.user_id = u.user_id
        """
        interactions_df = pd.read_sql(query, self.db.bind)
        
        if len(interactions_df) < 10:  # Not enough data
            return False
            
        # Convert timestamps to datetime
        interactions_df['created_at'] = pd.to_datetime(interactions_df['created_at'])
        interactions_df['user_created_at'] = pd.to_datetime(interactions_df['user_created_at'])
        
        # Feature engineering
        interactions_df['days_since_post'] = (pd.Timestamp.now() - interactions_df['created_at']).dt.days
        interactions_df['user_tenure_days'] = (pd.Timestamp.now() - interactions_df['user_created_at']).dt.days
        
        # Get post features
        post_query = """
        SELECT 
            p.post_id,
            p.created_at,
            LENGTH(p.content) as content_length,
            (SELECT COUNT(*) FROM like WHERE post_id = p.post_id) as like_count,
            (SELECT COUNT(*) FROM save WHERE post_id = p.post_id) as save_count,
            (SELECT COUNT(*) FROM comment WHERE post_id = p.post_id) as comment_count
        FROM post p
        """
        self.post_features = pd.read_sql(post_query, self.db.bind)
        self.post_features['created_at'] = pd.to_datetime(self.post_features['created_at'])
        self.post_features['days_since_post'] = (pd.Timestamp.now() - self.post_features['created_at']).dt.days
        
        # Normalize features
        for col in ['content_length', 'like_count', 'save_count', 'comment_count']:
            if self.post_features[col].max() > 0:
                self.post_features[col] = self.post_features[col] / self.post_features[col].max()
        
        # Prepare training data
        X = []
        y = []
        
        for _, row in interactions_df.iterrows():
            user_id = row['user_id']
            post_id = row['post_id']
            
            # Get post features
            post_row = self.post_features[self.post_features['post_id'] == post_id]
            if post_row.empty:
                continue
                
            # Create feature vector
            features = [
                post_row['days_since_post'].values[0],
                post_row['content_length'].values[0],
                post_row['like_count'].values[0],
                post_row['save_count'].values[0],
                post_row['comment_count'].values[0],
                row['user_tenure_days']
            ]
            
            X.append(features)
            y.append(row['interaction_value'])
        
        # Train model
        if len(X) > 0:
            self.model.fit(X, y)
            return True
        else:
            return False
    
    def rank_posts_for_user(self, user_id, post_ids=None, top_n=10):
        # Get user information
        user_query = f"""
        SELECT created_at FROM "user" WHERE user_id = '{user_id}'
        """
        user_df = pd.read_sql(user_query, self.db.bind)
        
        if user_df.empty:
            return []
            
        user_created_at = pd.to_datetime(user_df['created_at'].values[0])
        user_tenure_days = (pd.Timestamp.now() - user_created_at).dt.days.total_seconds() / (24 * 3600)
        
        # Filter posts if post_ids provided
        if post_ids:
            post_features = self.post_features[self.post_features['post_id'].isin(post_ids)]
        else:
            post_features = self.post_features
            
        # Prepare features for prediction
        X_pred = []
        post_ids_ordered = []
        
        for _, row in post_features.iterrows():
            features = [
                row['days_since_post'],
                row['content_length'],
                row['like_count'],
                row['save_count'],
                row['comment_count'],
                user_tenure_days
            ]
            X_pred.append(features)
            post_ids_ordered.append(row['post_id'])
            
        if not X_pred:
            return []
            
        # Predict scores
        scores = self.model.predict(X_pred)
        
        # Create recommendations
        recommendations = []
        for i, post_id in enumerate(post_ids_ordered):
            post_info = self.post_features[self.post_features['post_id'] == post_id]
            title_query = f"""
            SELECT title FROM post WHERE post_id = '{post_id}'
            """
            title_df = pd.read_sql(title_query, self.db.bind)
            
            if not title_df.empty:
                recommendations.append({
                    'post_id': post_id,
                    'title': title_df['title'].values[0],
                    'score': float(scores[i])
                })
                
        # Sort by predicted score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations[:top_n]