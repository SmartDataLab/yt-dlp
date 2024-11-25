from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    get_element_by_id,
    int_or_none,
    js_to_json,
    str_or_none,
    traverse_obj,
)



class ToutiaoIE(InfoExtractor):

    _VALID_URL = r'https://(?:www\.)?toutiao\.com/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.toutiao.com/video/7313853722689045004/',
        'info_dict' :{
            'id': '6996881461559165471',
            'ext': 'mp4',
            'title': '盲目涉水风险大，亲身示范高水位行车注意事项',
        }}]

    def _get_json_data(self, webpage, video_id):
        import urllib.parse
        import json
        js_data_raw = get_element_by_id("RENDER_DATA", webpage)
        decoded_string = urllib.parse.unquote(js_data_raw.replace(" ",""))
        # with open("toutiao_ssr.json", "w") as f:
        #     f.write(decoded_string)
        js_data = json.loads(decoded_string)
        return js_data
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        # print(video_id, webpage)
        json_data = self._get_json_data(webpage, video_id)
        formats = [ ]
        for one in json_data["data"]["initialVideo"]["videoPlayInfo"]["video_list"]:
            new_one = {
                    'url': one["main_url"],
                    'width': one["video_meta"]["vwidth"],
                    'height': one["video_meta"]["vheight"],
                    'fps': one["video_meta"]['fps'],
                    'vcodec': one["video_meta"]["codec_type"],
                    'format_id': one["video_meta"]["definition"],
                    'filesize': one["video_meta"]['size'],
                    'ext': one["video_meta"]["vtype"]}
            formats.append(new_one)
        return {
            "id" : video_id,
            "title" : json_data["data"]["initialVideo"]["title"],
            "publishTime" : json_data["data"]["initialVideo"]["publishTime"],
            "duration" : json_data["data"]["initialVideo"]["duration"],
            "formats": formats
        }

