title = "THE EFFECT OF MOBILE PHONES ON STUDENTS tr"

def extract_tags_from_title(title):
        """Extract meaningful tags from the book title"""
        # Common words to exclude from tags
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        # Split title into words and filter
        words = title.lower().split()
        meaningful_words = [word.strip('.,!?;:"()[]') for word in words 
                          if word.lower() not in stop_words and len(word) > 2]
        
        return meaningful_words