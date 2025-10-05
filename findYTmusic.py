import sys
from ytmusicapi import YTMusic
import argparse

# --- Configuration ---
# ytmusicapi can be initialized in "anonymous" mode for public searches
# For personalized features or library access, you'd need to provide authentication headers/cookies.
# For public search, anonymous mode is usually sufficient.

def ytmusicapi_search(query_terms, max_results=5):
    """
    Searches YouTube Music for tracks using ytmusicapi and returns relevant details.
    """
    try:
        # Initialize YTMusic in anonymous mode for public search
        ytmusic = YTMusic()
        
        # Perform the search. 'songs' type is most relevant for your request.
        # 'videos' type can also be used, but 'songs' is more specific to music tracks.
        search_results = ytmusic.search(query=query_terms, filter="songs", limit=max_results)

        results = []
        for item in search_results:
            # ytmusicapi returns structured data. We need to extract the fields.
            title = item.get("title", "N/A")
            
            # Artists can be a list of dictionaries in ytmusicapi, join their names.
            artists = ", ".join([artist["name"] for artist in item.get("artists", [])]) if item.get("artists") else "N/A"
            
            # ytmusicapi provides direct YouTube Music links for songs.
            link = f"https://music.youtube.com/watch?v={item['videoId']}"
            
            # Duration is often in seconds, convert to MM:SS
            duration_seconds = item.get("duration_seconds")
            duration_formatted = "N/A"
            if duration_seconds is not None:
                minutes = duration_seconds // 60
                seconds = duration_seconds % 60
                duration_formatted = f"{minutes:02d}:{seconds:02d}"

            # View count is not directly available in 'songs' search results from ytmusicapi's search function.
            # To get view count, you would typically need to fetch the video details using the official YouTube Data API,
            # or try to navigate to the video page and scrape it, which adds complexity.
            # For this reason, view count will be "N/A" or 0 using this method.
            # If view count is critical, the official API (with key) is superior.
            views = "N/A (Not available via ytmusicapi search results)"

            results.append({
                "title": title,
                "artist": artists,
                "link": link,
                "duration": duration_formatted,
                "views": views
            })
        return results

    except Exception as e:
        print(f"An error occurred with ytmusicapi: {e}", file=sys.stderr)
        return []

def main():
    parser = argparse.ArgumentParser(description="Search YouTube Music for tracks (without API key).")
    parser.add_argument("search_terms", help="The terms to search for on YouTube Music.")
    parser.add_argument("-n", "--num_results", type=int, default=5,
                        help="Number of top results to display (default: 5).")

    args = parser.parse_args()

    print(f"Searching YouTube Music for \"{args.search_terms}\" using ytmusicapi...")
    results = ytmusicapi_search(args.search_terms, args.num_results)

    if results:
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"Title: {result['title']}")
            print(f"Artist: {result['artist']}")
            print(f"Duration: {result['duration']}")
            print(f"Views: {result['views']}")
            print(f"Link: {result['link']}")
    else:
        print("No music found for your search terms.")

if __name__ == "__main__":
    main()