from sqlalchemy.orm import Session
from app.services.content_recommender import ContentBasedRecommender
from app.services.collaborative_recommender import CollaborativeRecommender
from app.services.learning_to_rank import LearningToRankRecommender

class AdvancedHybridRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.content_recommender = ContentBasedRecommender(db)
        self.collaborative_recommender = CollaborativeRecommender(db)
        self.learning_to_rank = LearningToRankRecommender(db)
        self.has_collab_data = False
        self.has_ranking_data = False
        
    def initialize(self):
        # Prepare all recommenders
        self.content_recommender.fetch_and_prepare_data()
        self.has_collab_data = self.collaborative_recommender.fetch_and_prepare_data()
        self.has_ranking_data = self.learning_to_rank.fetch_and_prepare_data()
        
    def get_personalized_feed(self, user_id, limit=20):
        # Get recommendations from all sources
        content_recs = []
        collab_recs = []
        
        # Get recommendations from content and collaborative approaches
        if self.has_collab_data:
            collab_recs = self.collaborative_recommender.get_recommendations(user_id, top_n=limit)
            
        # Use previously liked posts to find similar content
        liked_posts_query = f"""
        SELECT post_id FROM like WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 5
        """
        liked_posts_df = pd.read_sql(liked_posts_query, self.db.bind)
        
        for _, row in liked_posts_df.iterrows():
            similar_posts = self.content_recommender.get_recommendations(row['post_id'], top_n=5)
            content_recs.extend(similar_posts)
            
        # Combine all recommendations
        all_recs = []
        post_ids = set()
        
        # Add collaborative recommendations first (higher priority)
        for rec in collab_recs:
            if rec['post_id'] not in post_ids:
                all_recs.append(rec)
                post_ids.add(rec['post_id'])
                
        # Add content recommendations
        for rec in content_recs:
            if rec['post_id'] not in post_ids:
                all_recs.append(rec)
                post_ids.add(rec['post_id'])
                
        # If we have enough data, use learning to rank to re-rank the recommendations
        if self.has_ranking_data and all_recs:
            post_ids_list = [rec['post_id'] for rec in all_recs]
            ranked_recs = self.learning_to_rank.rank_posts_for_user(user_id, post_ids_list, top_n=limit)
            
            # If ranking was successful, use it
            if ranked_recs:
                return ranked_recs
                
        # Otherwise return the combined recommendations
        return all_recs[:limit]
        
    def get_post_recommendations(self, user_id, post_id, limit=10):
        # Get content-based recommendations for the post
        content_recs = self.content_recommender.get_recommendations(post_id, top_n=limit*2)
        
        # If we have enough data, use learning to rank to re-rank the recommendations
        if self.has_ranking_data and content_recs:
            post_ids = [rec['post_id'] for rec in content_recs]
            ranked_recs = self.learning_to_rank.rank_posts_for_user(user_id, post_ids, top_n=limit)
            
            # If ranking was successful, use it
            if ranked_recs:
                return ranked_recs
                
        # Otherwise return the content recommendations
        return content_recs[:limit]