import os
import subprocess
from rich.console import Console
from rich import box
from html import escape
from rich.table import Table
from dotenv import load_dotenv
from rich import print
from prompt_toolkit import print_formatted_text
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import clear, yes_no_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, ANSI

load_dotenv()
API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Constants
max_results_v = 25
max_results_pl = 15
splack_logo = '''
              8               8      
              8               8
.oPYo. .oPYo. 8 .oPYo. .oPYo. 8  .o
Yb..   8    8 8 .oooo8 8    ' 8oP'
  'Yb. 8    8 8 8    8 8    . 8 `b.
`YooP' 8YooP' 8 `YooP8 `YooP' 8  `o.
:.....:8 ....:..:.....::.....:..::...
:::::::8 ::::::::::::::::::::::::::::
:::::::..::::::::::::::::::::::::::::
'''

status_msg = "Press Ctrl-C to exit"
# Styling for prompt_toolkit
style = Style.from_dict({
    'title': '#ff9d00',
    'channel': '#00ff00',
    'video-id': '#009dff',
    'descriptiontext': '#7f7f7f',
    'prompter': '#71bde9',
    'underline': 'underline',
    'nores': '#ff0000',
    'skyblue': '#71bde9'
})

def stream_video(video_id):
    real_URL = f"https://www.youtube.com/watch?v={video_id}"
    command = f"mpv {real_URL} --ytdl --input-default-bindings --osc=yes --no-video --prefetch-playlist=yes --ytdl-raw-options=yes-playlist="
    
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while streaming: {e}")

def search_youtube(query, search_type='video', max_results=max_results_v):
    if not query:
        print("Please provide a search query.")
        return []
    
    results = []
    page_token = None
    while len(results) < max_results:
        request = youtube.search().list(
            part="snippet",
            maxResults=min(max_results - len(results), 50),
            q=query,
            type=search_type,
            topicId="/m/04rlf" # Music topic ID, possibly deprecated
        )
        if page_token is not None:
            request.pageToken = page_token
        response = request.execute()

        if 'items' not in response:
            print_formatted_text(HTML("No results found."), style=style)
            return []

        for item in response['items']:
            if 'snippet' not in item:
                continue

            snippet = item['snippet']
            if search_type == 'video':
                if 'title' not in snippet or 'videoId' not in item['id']:
                    continue
                results.append({
                    'title': snippet['title'],
                    'videoId': item['id']['videoId'],
                    'channelTitle': snippet.get('channelTitle', ''),
                    'description': snippet.get('description', '')
                })
            elif search_type == 'playlist':
                if 'title' not in snippet or 'playlistId' not in item['id']:
                    continue
                results.append({
                    'title': snippet['title'],
                    'playlistId': item['id']['playlistId'],
                    'channelTitle': snippet.get('channelTitle', ''),
                    'description': snippet.get('description', '')
                })
        
        page_token = response.get('nextPageToken')

    if not results:
        print_formatted_text(HTML("No results found."), style=style)
        return []

    return results[:max_results]

def get_playlist_items(playlist_id, max_results=max_results_pl):
    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=max_results,
        playlistId=playlist_id
    )
    response = request.execute()
    
    results_show = []
    for item in response.get('items', []):
        snippet = item.get('snippet')
        if snippet is not None and 'resourceId' in snippet:
            video_id = snippet['resourceId'].get('videoId')
            if video_id is not None:
                results_show.append({
                    'title': snippet.get('title'),
                    'videoId': video_id
                })
    for i, result in enumerate(results_show, 1):
        
        print_formatted_text(HTML(f" {i}. {escape(result['title'])}"))
    return results_show

def stream_playlist(playlist_id):
    videos = get_playlist_items(playlist_id)
    if not videos:
        print_formatted_text(HTML("<u>No videos found in the playlist</u>"))
        return

    for i, video in enumerate(videos, 1):
        try:
            if video and 'title' in video and 'videoId' in video:
                print(f"\nPlaying video {i}/{len(videos)}: {video['title']}")
                stream_video(video['videoId'])
            else:
                print(f"\nSkipping video {i}/{len(videos)}: video is invalid")
        except Exception as e:
            print(f"An error occurred processing video {i}/{len(videos)}: {e}")

def quit_dialog():
    yn_result = yes_no_dialog(
        title="Yes/No dialog example", text="Press ENTER to quit."
    ).run()

    if yn_result == True:
        quit()
    else:
        print("Canceled")
        main()


def get_toolbar():
    
    return HTML(status_msg)


def main():
    global status_msg
    try:
        print_formatted_text(ANSI(splack_logo), style=style)
        while True:
            
            search_type = prompt(HTML("<style>Do you want to search for (<skyblue>v</skyblue>)ideo or (<skyblue>p</skyblue>)laylist? </style>"), style=style, bottom_toolbar=get_toolbar, refresh_interval=0.02).lower()
            if search_type not in ['v', 'p']:
                status_msg = "Invalid option. Please choose 'v' for video or 'p' for playlist."
                print_formatted_text(HTML("Invalid option. Please choose '<skyblue>v</skyblue>' for video or '<skyblue>p</skyblue>' for playlist.\n"), style=style)
                continue

            query = prompt(HTML("Enter your search query: "), style=style, bottom_toolbar=get_toolbar, refresh_interval=0.02)
            if not query:
                status_msg = "Please enter a valid search query."
                print_formatted_text(HTML("Please enter a valid search query"), style=style)
                continue

            max_results = int(prompt("How many results do you want to display? ", default=str(max_results_v), style=style, bottom_toolbar=get_toolbar, refresh_interval=0.02))

            if search_type == 'v':
                results = search_youtube(query, 'video', max_results)
            else:
                results = search_youtube(query, 'playlist', max_results)

            if not results:
                status_msg = "No results found."
                print("No results!")
                continue

            table = Table(title="Search Results", show_header=True, header_style="italic", expand=False, safe_box=True, collapse_padding=True, box=box.HEAVY)
            table.add_column(" # ", style="#f0f0f0", min_width=4, no_wrap=True)
            table.add_column("Title", style="#88ccdd", max_width=35, no_wrap=True)
            table.add_column("Link", style="#ff33ee", max_width=10, no_wrap=True)
            table.add_column("Description", style="dim #c5c5c5", no_wrap=True)
            
            for i, result in enumerate(results, start=1):
                #table.add_row(str(i), result['title'], result.get('description', '')[:100])
                real_URL = f"https://www.youtube.com/watch?v={result['videoId']}" if search_type == 'v' else f"https://www.youtube.com/playlist?list={result['playlistId']}"
                link = f"[link={real_URL}]{result['videoId'] if search_type == 'v' else result['playlistId']}[/link]"
                table.add_row(str(i), result['title'], link, result.get('description', '')[:100])
            console = Console()
            console.print(table)

            while True:
                choice = prompt(HTML("Enter the number of the video/playlist you want to play, or 0 to quit: "), style=style, bottom_toolbar=get_toolbar, refresh_interval=0.02)
                if choice == '0':
                    quit_dialog()
                    break
                if choice is not None:
                    try:
                        choice = int(choice)
                    except ValueError:
                        status_msg = "Invalid input. Please enter a valid number."
                        print_formatted_text(HTML("Invalid input. Please enter a valid number."), style=style)
                        continue
                else:
                    status_msg = "Invalid input. Please enter a valid number."
                    print_formatted_text(HTML("Invalid input. Please enter a valid number."), style=style)
                    continue
                if choice < 1 or choice > len(results):
                    print_formatted_text(HTML(f"Invalid choice. Please enter a number between 1 and {len(results)}."), style=style)
                    continue
                
                choice -= 1
                if search_type == 'v':
                    status_msg = f"Playing: {results[choice]['title']}"
                    print_formatted_text(HTML(f"Playing: <title>{escape(results[choice]['title'])}</title>"), style=style)
                    stream_video(results[choice]['videoId'])
                else:
                    stream_playlist(results[choice]['playlistId'])
                break
                    
    except HttpError as e:
        print_formatted_text(HTML(f"An HTTP error {e.resp.status} occurred:\n{e.content}"))
    except KeyboardInterrupt:
        print_formatted_text(HTML("\n<skyblue>Exiting!</skyblue>"), style=style)
        quit()
    except Exception as e:
        print_formatted_text(HTML(f"An error occurred: {e}"), style=style)
        

if __name__ == '__main__':
    clear()
    main()
