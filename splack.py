import os
import subprocess
from rich.console import Console
from rich import box
from html import escape
from rich.table import Table
from dotenv import load_dotenv
from rich import print
from prompt_toolkit import print_formatted_text
from prompt_toolkit.validation import Validator
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import clear, yes_no_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, ANSI
from prompt_toolkit.layout import Container, VSplit, HSplit, FormattedTextControl
from prompt_toolkit.widgets import Frame, FormattedTextToolbar, SearchToolbar, ValidationToolbar
import html
load_dotenv()
API_KEY = os.getenv('YT_API_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Constants
max_results_v = 40
max_results_pl = 25
global max_results


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



# Styling for prompt_toolkit
style = Style.from_dict({
    'title': '#e4963c',
    'logo': 'bold #e43c52',
    'video-id': '#009dff',
    'descriptiontext': '#7f7f7f',
    'underline': 'underline',
    'nores': '#ff0000',
    'bottom-toolbar': '#a1a1a1 bg:#1d1d1d',
    'bottom-toolbar.text': 'bold #757575',
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
    max_results = min(max_results, len(results))
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


def get_toolbar():

    return [('class:bottom-toolbar', ' Press Ctrl+C to exit.')]

def range_validator(text):
    if 0 < int(text) <= globals().get(int('max_results'), int(max_results_v)):
        return True

intvalidator = Validator.from_callable(
    lambda x: '0' < str(x) <= globals().get(str('max_results'), str(max_results_v)),
    error_message=f"Please enter a valid number between 1 and {max_results_v} for video or {max_results_pl} for playlist.",
    move_cursor_to_end=True
)

    
def main():
    try:
        print_formatted_text(HTML(f"<logo>{splack_logo}</logo>"), style=style)
        while True:                
            search_type = prompt(HTML("<style>Do you want to search for (<skyblue>v</skyblue>)ideo or (<skyblue>p</skyblue>)laylist? </style>"), style=style, bottom_toolbar=get_toolbar).lower()
            if search_type not in ['v', 'p']:
                print_formatted_text(HTML("Invalid option. Please choose '<skyblue>v</skyblue>' for video or '<skyblue>p</skyblue>' for playlist.\n"), style=style)
                continue

            query = prompt(HTML("Enter your search query: "), style=style, bottom_toolbar=get_toolbar)
            if not query:
                print_formatted_text(HTML("Please enter a valid search query\n"), style=style)
                continue

            max_results = int(prompt("How many results do you want to display? ", validator=intvalidator, validate_while_typing=False, style=style))

            if search_type == 'v':
                results = search_youtube(query, 'video', max_results)
            else:
                results = search_youtube(query, 'playlist', max_results)

            if not results:
                print("No results!")
                continue

            table = Table(title="Search Results", show_header=True, header_style="italic", expand=True, safe_box=True, collapse_padding=True, box=box.ROUNDED)
            table.add_column(" # ", style="#d3ad66", min_width=4, no_wrap=True)
            table.add_column("Title", style="#7feee3", max_width=45, no_wrap=True)
            table.add_column("Link", style="link #3131b1", max_width=10, no_wrap=True)
            table.add_column("Description", style="dim #ffffff", max_width=100, no_wrap=True)

            for i, result in enumerate(results, start=1):
                real_URL = f"https://www.youtube.com/watch?v={result['videoId']}" if search_type == 'v' else f"https://www.youtube.com/playlist?list={result['playlistId']}"
                link = f"[link={real_URL}]{result['videoId'] if search_type == 'v' else result['playlistId']}[/link]"
                title = html.unescape(result['title'])
                description = html.unescape(result.get('description', '')[:100])
                if not description:
                    description = "No description available"
                table.add_row(str(i), title, link, description)

            console = Console()
            console.print(table)

            while True:
                choice = prompt(HTML("\nEnter the number of the video/playlist you want to play, or 0 to quit: "), style=style, bottom_toolbar=get_toolbar, refresh_interval=0.02)
                if choice == '0':
                    quit()
                    break
                if choice is not None:
                    try:
                        choice = int(choice)

                    except ValueError:
                        print_formatted_text(HTML("Invalid input. Please enter a valid number.\n"), style=style)
                        continue
                else:
                    print_formatted_text(HTML("Invalid input. Please enter a valid number."), style=style)
                    continue
                
                
                choice -= 1

                if search_type == 'v':
                    stream_video(results[choice]['videoId'])
                else:
                    stream_playlist(results[choice]['playlistId'])
                break
    except HttpError as e:
        print_formatted_text(HTML(f"An HTTP error {e.resp.status} occurred:\n{e.content}"))
    except KeyboardInterrupt:
        print_formatted_text(HTML("<skyblue>Exiting!</skyblue>\n"), style=style)
        quit()
    except Exception as e:
        print_formatted_text(HTML(f"\nAn error occurred: {e}"), style=style)
        main()

if __name__ == '__main__':
    clear()
    main()
    
    
