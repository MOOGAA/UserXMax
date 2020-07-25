# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Userbot module containing various scrapers. """

import io
import os
import time
import asyncio
import shutil
import re
import requests
import urllib

from PIL import Image
from bs4 import BeautifulSoup
from html import unescape
from asyncio import sleep
from re import findall
from selenium import webdriver
from urllib.parse import quote_plus
from urllib.error import HTTPError
from selenium.webdriver.chrome.options import Options
from wikipedia import summary
from wikipedia.exceptions import DisambiguationError, PageError
from urbandict import define
from requests import get
from search_engine_parser import GoogleSearch
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googletrans import LANGUAGES, Translator
from gtts import gTTS
from gtts.lang import tts_langs
from emoji import get_emoji_regexp
from youtube_dl import YoutubeDL
from youtube_dl.utils import (DownloadError, ContentTooShortError,
                              ExtractorError, GeoRestrictedError,
                              MaxDownloadsReached, PostProcessingError,
                              UnavailableVideoError, XAttrMetadataError)

from ..help import add_help_item
from userbot import (BOTLOG, BOTLOG_CHATID, YOUTUBE_API_KEY,
                     CHROME_DRIVER, GOOGLE_CHROME_BIN, bot, OCR_SPACE_API_KEY, TEMP_DOWNLOAD_DIRECTORY)
from userbot.events import register
from telethon.tl.types import DocumentAttributeAudio
from userbot.modules.misc.upload_download import progress
from google_images_download import google_images_download

TTS_LANG = "en"
TRT_LANG = "en"

opener = urllib.request.build_opener()
useragent = ('Mozilla/5.0 (Linux; Android 10; SM-G975F) '
             'AppleWebKit/537.36 (KHTML, like Gecko) '
             'Chrome/80.0.3987.149 Mobile Safari/537.36'
             )
opener.addheaders = [('User-agent', useragent)]


@register(outgoing=True, pattern="^.img (.*)")
async def img_sampler(event):
    """ For .img command, search and return images matching the query. """
    await event.edit("Processing...")
    query = event.pattern_match.group(1)
    lim = findall(r"lim=\d+", query)
    try:
        lim = lim[0]
        lim = lim.replace("lim=", "")
        query = query.replace("lim=" + lim[0], "")
    except IndexError:
        lim = 2
    response = google_images_download.googleimagesdownload()

    # creating list of arguments
    arguments = {
        "keywords": query,
        "limit": lim,
        "format": "jpg",
        "no_directory": "no_directory"
    }

    # passing the arguments to the function
    paths = response.download(arguments)
    lst = paths[0][query]
    await event.client.send_file(
        await event.client.get_input_entity(event.chat_id), lst)
    rmtree(os.path.dirname(os.path.abspath(lst[0])))
    await event.delete()


@register(outgoing=True, pattern="^\.currency (.*)")
async def moni(event):
    input_str = event.pattern_match.group(1)
    input_sgra = input_str.split(" ")
    if len(input_sgra) == 3:
        try:
            number = float(input_sgra[0])
            currency_from = input_sgra[1].upper()
            currency_to = input_sgra[2].upper()
            request_url = "https://api.exchangeratesapi.io/latest?base={}".format(
                currency_from)
            current_response = get(request_url).json()
            if currency_to in current_response["rates"]:
                current_rate = float(current_response["rates"][currency_to])
                rebmun = round(number * current_rate, 2)
                await event.edit("{} {} = {} {}".format(
                    number, currency_from, rebmun, currency_to))
            else:
                await event.edit(
                    "`This seems to be some alien currency, which I can't convert right now.`"
                )
        except Exception as e:
            await event.edit(str(e))
    else:
        return await event.edit("`Invalid syntax.`")


@register(outgoing=True, pattern=r"^\.google (.*)")
async def gsearch(q_event):
    """ For .google command, do a Google search. """
    match = q_event.pattern_match.group(1)
    page = findall(r"page=\d+", match)
    try:
        page = page[0]
        page = page.replace("page=", "")
        match = match.replace("page=" + page[0], "")
    except IndexError:
        page = 1
    search_args = (str(match), int(page))
    gsearch = GoogleSearch()
    gresults = await gsearch.async_search(*search_args)
    msg = ""
    for i in range(10):
        try:
            title = gresults["titles"][i]
            link = gresults["links"][i]
            desc = gresults["descriptions"][i]
            msg += f"[{title}]({link})\n`{desc}`\n\n"
        except IndexError:
            break
    await q_event.edit("**Search Query:**\n`" + match + "`\n\n**Results:**\n" +
                       msg,
                       link_preview=False)

    if BOTLOG:
        await q_event.client.send_message(
            BOTLOG_CHATID,
            "Google Search query `" + match + "` was executed successfully",
        )


@register(outgoing=True, pattern=r"^\.wiki (.*)")
async def wiki(wiki_q):
    """ For .wiki command, fetch content from Wikipedia. """
    match = wiki_q.pattern_match.group(1)
    try:
        summary(match)
    except DisambiguationError as error:
        return await wiki_q.edit(f"Disambiguated page found.\n\n{error}")
    except PageError as pageerror:
        return await wiki_q.edit(f"Page not found.\n\n{pageerror}")
    result = summary(match)
    if len(result) >= 4096:
        file = open("output.txt", "w+")
        file.write(result)
        file.close()
        await wiki_q.client.send_file(
            wiki_q.chat_id,
            "output.txt",
            reply_to=wiki_q.id,
            caption="`Output too large, sending as file`",
        )
        if os.path.exists("output.txt"):
            return os.remove("output.txt")
    await wiki_q.edit("**Search:**\n`" + match + "`\n\n**Result:**\n" + result)
    if BOTLOG:
        await wiki_q.client.send_message(
            BOTLOG_CHATID, f"Wiki query `{match}` was executed successfully")


@register(outgoing=True, pattern="^\.ud (.*)")
async def urban_dict(ud_e):
    """ For .ud command, fetch content from Urban Dictionary. """
    await ud_e.edit("Processing...")
    query = ud_e.pattern_match.group(1)
    try:
        define(query)
    except HTTPError:
        return await ud_e.edit(f"Sorry, couldn't find any results for: {query}")
    mean = define(query)
    deflen = sum(len(i) for i in mean[0]["def"])
    exalen = sum(len(i) for i in mean[0]["example"])
    meanlen = deflen + exalen
    if int(meanlen) >= 0:
        if int(meanlen) >= 4096:
            await ud_e.edit("`Output too large, sending as file.`")
            file = open("output.txt", "w+")
            file.write("Text: " + query + "\n\nMeaning: " + mean[0]["def"] +
                       "\n\n" + "Example: \n" + mean[0]["example"])
            file.close()
            await ud_e.client.send_file(
                ud_e.chat_id,
                "output.txt",
                caption="`Output was too large, sent it as a file.`")
            if os.path.exists("output.txt"):
                os.remove("output.txt")
            return await ud_e.delete()
        await ud_e.edit("Text: **" + query + "**\n\nMeaning: **" +
                        mean[0]["def"] + "**\n\n" + "Example: \n__" +
                        mean[0]["example"] + "__")
        if BOTLOG:
            await ud_e.client.send_message(
                BOTLOG_CHATID,
                "ud query `" + query + "` executed successfully.")
    else:
        await ud_e.edit("No result found for **" + query + "**")


@register(outgoing=True, pattern=r"^\.tts(?: |$)([\s\S]*)")
async def text_to_speech(query):
    """ For .tts command, a wrapper for Google Text-to-Speech. """
    textx = await query.get_reply_message()
    message = query.pattern_match.group(1)
    if message:
        pass
    elif textx:
        message = textx.text
    else:
        return await query.edit(
            "`Give a text or reply to a message for Text-to-Speech!`")

    try:
        gTTS(message, lang=TTS_LANG)
    except AssertionError:
        return await query.edit(
            'The text is empty.\n'
            'Nothing left to speak after pre-precessing, tokenizing and cleaning.'
        )
    except ValueError:
        return await query.edit('Language is not supported.')
    except RuntimeError:
        return await query.edit('Error loading the languages dictionary.')
    tts = gTTS(message, lang=TTS_LANG)
    tts.save("k.mp3")
    with open("k.mp3", "rb") as audio:
        linelist = list(audio)
        linecount = len(linelist)
    if linecount == 1:
        tts = gTTS(message, lang=TTS_LANG)
        tts.save("k.mp3")
    with open("k.mp3", "r"):
        await query.client.send_file(query.chat_id, "k.mp3", voice_note=True)
        os.remove("k.mp3")
        if BOTLOG:
            await query.client.send_message(
                BOTLOG_CHATID, "Text to Speech executed successfully !")
        await query.delete()


# kanged from Blank-x ;---;
@register(outgoing=True, pattern="^\.imdb (.*)")
async def imdb(e):
    try:
        movie_name = e.pattern_match.group(1)
        remove_space = movie_name.split(' ')
        final_name = '+'.join(remove_space)
        page = get("https://www.imdb.com/find?ref_=nv_sr_fn&q=" + final_name +
                   "&s=all")
        soup = BeautifulSoup(page.content, 'lxml')
        odds = soup.findAll("tr", "odd")
        mov_title = odds[0].findNext('td').findNext('td').text
        mov_link = "http://www.imdb.com/" + \
            odds[0].findNext('td').findNext('td').a['href']
        page1 = get(mov_link)
        soup = BeautifulSoup(page1.content, 'lxml')
        if soup.find('div', 'poster'):
            poster = soup.find('div', 'poster').img['src']
        else:
            poster = ''
        if soup.find('div', 'title_wrapper'):
            pg = soup.find('div', 'title_wrapper').findNext('div').text
            mov_details = re.sub(r'\s+', ' ', pg)
        else:
            mov_details = ''
        credits = soup.findAll('div', 'credit_summary_item')
        if len(credits) == 1:
            director = credits[0].a.text
            writer = 'Not available'
            stars = 'Not available'
        elif len(credits) > 2:
            director = credits[0].a.text
            writer = credits[1].a.text
            actors = []
            for x in credits[2].findAll('a'):
                actors.append(x.text)
            actors.pop()
            stars = actors[0] + ',' + actors[1] + ',' + actors[2]
        else:
            director = credits[0].a.text
            writer = 'Not available'
            actors = []
            for x in credits[1].findAll('a'):
                actors.append(x.text)
            actors.pop()
            stars = actors[0] + ',' + actors[1] + ',' + actors[2]
        if soup.find('div', "inline canwrap"):
            story_line = soup.find('div',
                                   "inline canwrap").findAll('p')[0].text
        else:
            story_line = 'Not available'
        info = soup.findAll('div', "txt-block")
        if info:
            mov_country = []
            mov_language = []
            for node in info:
                a = node.findAll('a')
                for i in a:
                    if "country_of_origin" in i['href']:
                        mov_country.append(i.text)
                    elif "primary_language" in i['href']:
                        mov_language.append(i.text)
        if soup.findAll('div', "ratingValue"):
            for r in soup.findAll('div', "ratingValue"):
                mov_rating = r.strong['title']
        else:
            mov_rating = 'Not available'
        await e.edit('<a href=' + poster + '>&#8203;</a>'
                     '<b>Title : </b><code>' + mov_title + '</code>\n<code>' +
                     mov_details + '</code>\n<b>Rating : </b><code>' +
                     mov_rating + '</code>\n<b>Country : </b><code>' +
                     mov_country[0] + '</code>\n<b>Language : </b><code>' +
                     mov_language[0] + '</code>\n<b>Director : </b><code>' +
                     director + '</code>\n<b>Writer : </b><code>' + writer +
                     '</code>\n<b>Stars : </b><code>' + stars +
                     '</code>\n<b>IMDB Url : </b>' + mov_link +
                     '\n<b>Story Line : </b>' + story_line,
                     link_preview=True,
                     parse_mode='HTML')
    except IndexError:
        await e.edit("Plox enter **Valid movie name** kthx")


@register(outgoing=True, pattern=r"^\.trt(?: |$)([\s\S]*)")
async def translateme(trans):
    """ For .trt command, translate the given text using Google Translate. """
    translator = Translator()
    textx = await trans.get_reply_message()
    message = trans.pattern_match.group(1)
    if message:
        pass
    elif textx:
        message = textx.text
    else:
        return await trans.edit("`Give a text or reply to a message to translate!`")

    try:
        reply_text = translator.translate(deEmojify(message), dest=TRT_LANG)
    except ValueError:
        return await trans.edit("Invalid destination language.")

    source_lan = LANGUAGES[f'{reply_text.src.lower()}']
    transl_lan = LANGUAGES[f'{reply_text.dest.lower()}']
    reply_text = f"From **{source_lan.title()}**\nTo **{transl_lan.title()}:**\n\n{reply_text.text}"

    await trans.edit(reply_text)
    if BOTLOG:
        await trans.client.send_message(
            BOTLOG_CHATID,
            f"Translated some {source_lan.title()} stuff to {transl_lan.title()} just now.",
        )


@register(pattern="\.lang (trt|tts) (.*)", outgoing=True)
async def lang(value):
    """ For .lang command, change the default langauge of userbot scrapers. """
    util = value.pattern_match.group(1).lower()
    if util == "trt":
        scraper = "Translator"
        global TRT_LANG
        arg = value.pattern_match.group(2).lower()
        if arg in LANGUAGES:
            TRT_LANG = arg
            LANG = LANGUAGES[arg]
        else:
            return await value.edit(
                f"`Invalid Language code !!`\n`Available language codes for TRT`:\n\n`{LANGUAGES}`"
            )
    elif util == "tts":
        scraper = "Text to Speech"
        global TTS_LANG
        arg = value.pattern_match.group(2).lower()
        if arg in tts_langs():
            TTS_LANG = arg
            LANG = tts_langs()[arg]
        else:
            return await value.edit(
                f"`Invalid Language code !!`\n`Available language codes for TTS`:\n\n`{tts_langs()}`"
            )
    await value.edit(f"`Language for {scraper} changed to {LANG.title()}.`")
    if BOTLOG:
        await value.client.send_message(
            BOTLOG_CHATID,
            f"`Language for {scraper} changed to {LANG.title()}.`")


@register(outgoing=True, pattern="^\.yt (.*)")
async def yt_search(video_q):
    """ For .yt command, do a YouTube search from Telegram. """
    query = video_q.pattern_match.group(1)
    result = ''

    if not YOUTUBE_API_KEY:
        return await video_q.edit(
            "`Error: YouTube API key missing! Add it to environment vars or config.env.`"
        )

    await video_q.edit("```Processing...```")

    full_response = await youtube_search(query)
    videos_json = full_response[1]

    for video in videos_json:
        title = f"{unescape(video['snippet']['title'])}"
        link = f"https://youtu.be/{video['id']['videoId']}"
        result += f"{title}\n{link}\n\n"

    reply_text = f"**Search Query:**\n`{query}`\n\n**Results:**\n\n{result}"

    await video_q.edit(reply_text)


async def ocr_space_file(filename,
                         overlay=False,
                         api_key=OCR_SPACE_API_KEY,
                         language='eng'):
    """ OCR.space API request with local file.
        Python3.5 - not tested on 2.7
    :param filename: Your file path & name.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
                    Defaults to 'helloworld'.
    :param language: Language code to be used in OCR.
                    List of available language codes can be found on https://ocr.space/OCRAPI
                    Defaults to 'en'.
    :return: Result in JSON format.
    """

    payload = {
        'isOverlayRequired': overlay,
        'apikey': api_key,
        'language': language,
    }
    with open(filename, 'rb') as f:
        r = requests.post(
            'https://api.ocr.space/parse/image',
            files={filename: f},
            data=payload,
        )
    return r.json()


@register(pattern=r".ocr (.*)", outgoing=True)
async def ocr(event):
    if not OCR_SPACE_API_KEY:
        return await event.edit(
            "`Error: OCR.Space API key is missing! Add it to environment variables or config.env.`"
        )
    await event.edit("`Reading...`")
    if not os.path.isdir(TEMP_DOWNLOAD_DIRECTORY):
        os.makedirs(TEMP_DOWNLOAD_DIRECTORY)
    lang_code = event.pattern_match.group(1)
    downloaded_file_name = await bot.download_media(
        await event.get_reply_message(), TEMP_DOWNLOAD_DIRECTORY)
    test_file = await ocr_space_file(filename=downloaded_file_name,
                                     language=lang_code)
    try:
        ParsedText = test_file["ParsedResults"][0]["ParsedText"]
    except BaseException:
        await event.edit("`Couldn't read it.`\n`I guess I need new glasses.`")
    else:
        await event.edit(f"`Here's what I could read from it:`\n\n{ParsedText}"
                         )
    os.remove(downloaded_file_name)


async def youtube_search(query,
                         order="relevance",
                         token=None,
                         location=None,
                         location_radius=None):
    """ Do a YouTube search. """
    youtube = build('youtube',
                    'v3',
                    developerKey=YOUTUBE_API_KEY,
                    cache_discovery=False)
    search_response = youtube.search().list(
        q=query,
        type="video",
        pageToken=token,
        order=order,
        part="id,snippet",
        maxResults=10,
        location=location,
        locationRadius=location_radius).execute()

    videos = []

    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            videos.append(search_result)
    try:
        nexttok = search_response["nextPageToken"]
        return (nexttok, videos)
    except HttpError:
        nexttok = "last_page"
        return (nexttok, videos)
    except KeyError:
        nexttok = "KeyError, try again."
        return (nexttok, videos)


@register(outgoing=True, pattern=r"\.rip(audio|video) (.*)")
async def download_video(v_url):
    """ For .rip command, download media from YouTube and many other sites. """
    url = v_url.pattern_match.group(2)
    type = v_url.pattern_match.group(1).lower()

    await v_url.edit("`Preparing to download...`")

    if type == "audio":
        opts = {
            'format':
            'bestaudio',
            'addmetadata':
            True,
            'key':
            'FFmpegMetadata',
            'writethumbnail':
            True,
            'prefer_ffmpeg':
            True,
            'geo_bypass':
            True,
            'nocheckcertificate':
            True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl':
            '%(id)s.mp3',
            'quiet':
            True,
            'logtostderr':
            False
        }
        video = False
        song = True

    elif type == "video":
        opts = {
            'format':
            'best',
            'addmetadata':
            True,
            'key':
            'FFmpegMetadata',
            'prefer_ffmpeg':
            True,
            'geo_bypass':
            True,
            'nocheckcertificate':
            True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'outtmpl':
            '%(id)s.mp4',
            'logtostderr':
            False,
            'quiet':
            True
        }
        song = False
        video = True

    try:
        await v_url.edit("`Fetching data, please wait..`")
        with YoutubeDL(opts) as rip:
            rip_data = rip.extract_info(url)
    except DownloadError as DE:
        return await v_url.edit(f"`{str(DE)}`")
    except ContentTooShortError:
        return await v_url.edit("`The download content was too short.`")
    except GeoRestrictedError:
        return await v_url.edit(
            "`Video is not available from your geographic location "
            "due to geographic restrictions imposed by a website.`"
        )
    except MaxDownloadsReached:
        return await v_url.edit("`Max-downloads limit has been reached.`")
    except PostProcessingError:
        return await v_url.edit("`There was an error during post processing.`")
    except UnavailableVideoError:
        return await v_url.edit("`Media is not available in the requested format.`")
    except XAttrMetadataError as XAME:
        return await v_url.edit(f"`{XAME.code}: {XAME.msg}\n{XAME.reason}`")
    except ExtractorError:
        return await v_url.edit("`There was an error during info extraction.`")
    except Exception as e:
        return await v_url.edit(f"{str(type(e)): {str(e)}}")
    c_time = time.time()
    if song:
        await v_url.edit(
            f"`Preparing to upload song:`\n**{rip_data['title']}**"
            "\nby *{rip_data['uploader']}*")
        await v_url.client.send_file(
            v_url.chat_id,
            f"{rip_data['id']}.mp3",
            supports_streaming=True,
            attributes=[
                DocumentAttributeAudio(duration=int(rip_data['duration']),
                                       title=str(rip_data['title']),
                                       performer=str(rip_data['uploader']))
            ],
            progress_callback=lambda d, t: asyncio.get_event_loop(
            ).create_task(
                progress(d, t, v_url, c_time, "Uploading..",
                         f"{rip_data['title']}.mp3")))
        os.remove(f"{rip_data['id']}.mp3")
        await v_url.delete()
    elif video:
        await v_url.edit(
            f"`Preparing to upload video:`\n**{rip_data['title']}**"
            "\nby *{rip_data['uploader']}*")
        await v_url.client.send_file(
            v_url.chat_id,
            f"{rip_data['id']}.mp4",
            supports_streaming=True,
            caption=rip_data['title'],
            progress_callback=lambda d, t: asyncio.get_event_loop(
            ).create_task(
                progress(d, t, v_url, c_time, "Uploading..",
                         f"{rip_data['title']}.mp4")))
        os.remove(f"{rip_data['id']}.mp4")
        await v_url.delete()


@register(outgoing=True, pattern=r"^.reverse(?: |$)(\d*)")
async def okgoogle(img):
    """ For .reverse command, Google search images and stickers. """
    if os.path.isfile("okgoogle.png"):
        os.remove("okgoogle.png")

    message = await img.get_reply_message()
    if message and message.media:
        photo = io.BytesIO()
        await bot.download_media(message, photo)
    else:
        return await img.edit("`Reply to photo or sticker nigger.`")

    if photo:
        await img.edit("`Processing...`")
        try:
            image = Image.open(photo)
        except OSError:
            return await img.edit('`Unsupported sexuality, most likely.`')
        name = "okgoogle.png"
        image.save(name, "PNG")
        image.close()
        # https://stackoverflow.com/questions/23270175/google-reverse-image-search-using-post-request#28792943
        searchUrl = 'https://www.google.com/searchbyimage/upload'
        multipart = {
            'encoded_image': (name, open(name, 'rb')),
            'image_content': ''
        }
        response = requests.post(searchUrl,
                                 files=multipart,
                                 allow_redirects=False)
        fetchUrl = response.headers['Location']

        if response != 400:
            await img.edit("`Image successfully uploaded to Google. Maybe.`"
                           "\n`Parsing source now. Maybe.`")
        else:
            return await img.edit("`Google told me to fuck off.`")

        os.remove(name)
        match = await ParseSauce(fetchUrl +
                                 "&preferences?hl=en&fg=1#languages")
        guess = match['best_guess']
        imgspage = match['similar_images']

        if guess and imgspage:
            await img.edit(f"[{guess}]({fetchUrl})\n\n`Looking for images...`")
        else:
            return await img.edit("`Couldn't find anything for your uglyass.`")

        if img.pattern_match.group(1):
            lim = img.pattern_match.group(1)
        else:
            lim = 3
        images = await scam(match, lim)
        yeet = []
        for i in images:
            k = requests.get(i)
            yeet.append(k.content)
        try:
            await img.client.send_file(entity=await
                                       img.client.get_input_entity(img.chat_id
                                                                   ),
                                       file=yeet,
                                       reply_to=img)
        except TypeError:
            pass
        await img.edit(
            f"[{guess}]({fetchUrl})\n\n[Visually similar images]({imgspage})")


async def ParseSauce(googleurl):
    """Parse/Scrape the HTML code for the info we want."""

    source = opener.open(googleurl).read()
    soup = BeautifulSoup(source, 'html.parser')

    results = {'similar_images': '', 'best_guess': ''}

    try:
        for similar_image in soup.findAll('input', {'class': 'gLFyf'}):
            url = 'https://www.google.com/search?tbm=isch&q=' + \
                urllib.parse.quote_plus(similar_image.get('value'))
            results['similar_images'] = url
    except BaseException:
        pass

    for best_guess in soup.findAll('div', attrs={'class': 'r5a77d'}):
        results['best_guess'] = best_guess.get_text()

    return results


async def scam(results, lim):

    single = opener.open(results['similar_images']).read()
    decoded = single.decode('utf-8')

    imglinks = []
    counter = 0

    pattern = r'^,\[\"(.*[.png|.jpg|.jpeg])\",[0-9]+,[0-9]+\]$'
    oboi = re.findall(pattern, decoded, re.I | re.M)

    for imglink in oboi:
        counter += 1
        if not counter >= int(lim):
            imglinks.append(imglink)
        else:
            break

    return imglinks


def deEmojify(inputString):
    """ Remove emojis and other non-safe characters from string """
    return get_emoji_regexp().sub(u'', inputString)


add_help_item(
    "scrapers",
    "Misc",
    "Userbot module containing various scrapers.",
    """
    `.img <search_query>`
    **Usage:** Does an image search on Google and shows 5 images.

    `.currency <amount> <from> <to>`
    **Usage:** Converts various currencies for you.

    `.google <query>`
    **Usage:** Does a search on Google.
 
    `.wiki <query>`
    **Usage:** Does a search on Wikipedia.

    `.ud <query>`
    **Usage:** Does a search on Urban Dictionary.

    `.tts <text> [or reply]`
    **Usage:** Translates text to speech for the language which is set.
    Use `.lang tts <language code>` to set language for tts. (Default is English)

    `.trt <text> [or reply]`
    **Usage:** Translates text to the language which is set.
    Use `.lang trt <language code>` to set language for trt. (Default is English)

    `.ocr <language Code>`
    Usage: Reply to an image or sticker to extract text from it..

    `.yt <text>`
    Usage: Does a YouTube search.

    `.imdb <movie-name>`
    **Usage:** Shows movie info and other stuff.

    `.ripaudio <url> or ripvideo <url>`
    **Usage:** Download videos and songs from YouTube 
    (and [many other sites](https://ytdl-org.github.io/youtube-dl/supportedsites.html)).
    
    `.reverse`
    **Usage:** Reply to a pic/sticker to revers-search it on Google Images.
    """
)
