from sqlalchemy.orm import Session
from app.services.content_recommender import ContentBasedRecommender
from app.services.collaborative_recommender import CollaborativeRecommender

class HybridRecommender:
    def __init__(self, db: Session):
        self.db = db
        self.content_recommender = ContentBasedRecommender(db)
        self.collaborative_recommender = CollaborativeRecommender(db)
        
    def initialize(self):
        # Prepare both recommenders
        self.content_recommender.fetch_and_prepare_data()
        collab_success = self.collaborative_recommender.fetch_and_prepare_data()
        return collab_success
    
    def get_recommendations_for_user(self, user_id, post_id=None, top_n=10):
        # Initialize content-based recommendations
        content_recs = []
        if post_id:
            content_recs = self.content_recommender.get_recommendations(post_id, top_n=top_n)
        
        # Try to get collaborative recommendations
        try:
            collab_recs = self.collaborative_recommender.get_recommendations(user_id, top_n=top_n)
        except:
            collab_recs = []
            
        # If we have both types of recommendations, blend them
        if content_recs and collab_recs:
            # Create dict of content recs for O(1) lookup
            content_dict = {rec['post_id']: rec for rec in content_recs}
            
            # Create a blended score
            blended_recs = []
            
            # Process collaborative recs first
            for rec in collab_recs:
                post_id = rec['post_id']
                # If post is also in content recs, boost its score
                if post_id in content_dict:
                    blended_recs.append({
                        'post_id': post_id,
                        'title': rec['title'],
                        'username': content_dict[post_id].get('username', 'unknown'),
                        'score': rec['score'] * 1.2  # Boost score
                    })
                    del content_dict[post_id]  # Remove to avoid duplication
                else:
                    blended_recs.append({
                        'post_id': post_id,
                        'title': rec['title'],
                        'username': 'unknown',
                        'score': rec['score']
                    })
            
            # Add remaining content recs
            for post_id, rec in content_dict.items():
                blended_recs.append({
                    'post_id': post_id,
                    'title': rec['title'],
                    'username': rec['username'],
                    'score': 0.5  # Lower base score for pure content matches
                })
            
            # Sort by score and take top_n
            blended_recs.sort(key=lambda x: x['score'], reverse=True)
            return blended_recs[:top_n]
            
        # If we only have one type, return that
        elif content_recs:
            return content_recs
        elif collab_recs:
            return collab_recs
        else:
            return []