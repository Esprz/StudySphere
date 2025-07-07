import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

class ContentBasedRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.post_df = None
        self.tfidf_matrix = None
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            min_df=2,
            max_features=5000
        )
        
    def fetch_and_prepare_data(self):
        # Execute SQL to get posts with content and metadata
        query = """
        SELECT p.post_id, p.title, p.content, 
               u.username, u.display_name
        FROM post p
        JOIN "user" u ON p.user_id = u.user_id
        """
        self.post_df = pd.read_sql(query, self.db.bind)
        
        # Create a combined text field for TF-IDF
        self.post_df['combined_text'] = (
            self.post_df['title'] + ' ' + 
            self.post_df['content'] + ' ' + 
            self.post_df['display_name']
        )
        
        # Create TF-IDF matrix
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(
            self.post_df['combined_text']
        )
        
        return self.post_df
    
    def get_recommendations(self, post_id, top_n=5):
        # Find post index
        post_index = self.post_df[self.post_df['post_id'] == post_id].index
        if len(post_index) == 0:
            return []
        
        post_index = post_index[0]
        
        # Get similarity scores
        cosine_sim = cosine_similarity(
            self.tfidf_matrix[post_index:post_index+1], 
            self.tfidf_matrix
        ).flatten()
        
        # Get top similar posts (excluding the post itself)
        similar_indices = cosine_sim.argsort()[::-1][1:top_n+1]
        
        # Return recommended posts
        return self.post_df.iloc[similar_indices][['post_id', 'title', 'username']].to_dict('records')