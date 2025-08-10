import pandas as pd
import numpy as np
from scipy.sparse.linalg import svds
from sqlalchemy.orm import Session

class CollaborativeRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.user_post_matrix = None
        self.post_df = None
        self.user_df = None
        self.user_features = None
        self.post_features = None
        
    def fetch_and_prepare_data(self):
        # Get all likes
        likes_query = """
        SELECT user_id, post_id FROM like
        """
        likes_df = pd.read_sql(likes_query, self.db.bind)
        
        # Get all posts
        posts_query = """
        SELECT post_id, title FROM post
        """
        self.post_df = pd.read_sql(posts_query, self.db.bind)
        
        # Get all users
        users_query = """
        SELECT user_id, username FROM "user"
        """
        self.user_df = pd.read_sql(users_query, self.db.bind)
        
        # Create user-post matrix (1 if user liked post, 0 otherwise)
        if len(likes_df) > 0:
            # Create pivot table
            self.user_post_matrix = likes_df.pivot_table(
                index='user_id', 
                columns='post_id',
                aggfunc=lambda x: 1,
                fill_value=0
            )
            
            # Apply SVD
            U, sigma, Vt = svds(self.user_post_matrix.values, k=min(10, min(self.user_post_matrix.shape)-1))
            
            # Convert to diagonal matrix
            sigma = np.diag(sigma)
            
            # Get user and post features
            self.user_features = U.dot(sigma)
            self.post_features = Vt.T
            
            return True
        else:
            return False
        
    def get_recommendations(self, user_id, top_n=5):
        # Check if user exists in matrix
        if user_id not in self.user_post_matrix.index:
            return []
        
        # Get user index
        user_idx = list(self.user_post_matrix.index).index(user_id)
        
        # Get user's predicted ratings for all posts
        user_pred = self.user_features[user_idx].dot(self.post_features.T)
        
        # Get posts the user has already liked
        user_liked_posts = set(self.user_post_matrix.columns[
            self.user_post_matrix.loc[user_id] > 0
        ])
        
        # Get top recommended posts the user hasn't liked yet
        post_indices = self.user_post_matrix.columns
        post_scores = [(post_id, score) for post_id, score in zip(post_indices, user_pred) 
                      if post_id not in user_liked_posts]
        
        # Sort by predicted score
        top_posts = sorted(post_scores, key=lambda x: x[1], reverse=True)[:top_n]
        
        # Get post details
        recommendations = []
        for post_id, _ in top_posts:
            post_info = self.post_df[self.post_df['post_id'] == post_id]
            if not post_info.empty:
                recommendations.append({
                    'post_id': post_id,
                    'title': post_info.iloc[0]['title'],
                    'score': float(_)
                })
        
        return recommendations