import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_id,
    int_or_none,
    js_to_json,
    str_or_none,
    traverse_obj,
)


class IxiguaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?ixigua\.com/(?:video/)?(?P<id>\d+).+'
    _TESTS = [{
        'url': 'https://www.ixigua.com/6996881461559165471',
        'info_dict': {
            'id': '6996881461559165471',
            'ext': 'mp4',
            'title': '盲目涉水风险大，亲身示范高水位行车注意事项',
            'description': 'md5:8c82f46186299add4a1c455430740229',
            'tags': ['video_car'],
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'uploader': '懂车帝原创',
            'uploader_id': '6480145787',
            'thumbnail': r're:^https?://.+\.(avif|webp)',
            'timestamp': 1629088414,
            'duration': 1030,
        }
    }]

    def _get_json_data(self, webpage, video_id):
        # print(webpage)
        with open("xigua.html", "w") as f:
            f.write(webpage)
        js_data = get_element_by_id('SSR_HYDRATED_DATA', webpage)
        with open("xigua_ssr.json", "w") as f:
            f.write(js_data)
        # print(js_data)
        if not js_data:
            if self._cookies_passed:
                raise ExtractorError('Failed to get SSR_HYDRATED_DATA')
            raise ExtractorError('Cookies (not necessarily logged in) are needed', expected=True)

        return self._parse_json(
            js_data.replace('window._SSR_HYDRATED_DATA=', ''), video_id, transform_source=js_to_json)

    def _media_selector(self, json_data):
        for path, override in (
            (('video_list', ), {}),
            (('dynamic_video', 'dynamic_video_list'), {'acodec': 'none'}),
            (('dynamic_video', 'dynamic_audio_list'), {'vcodec': 'none', 'ext': 'm4a'}),
        ):
            for media in traverse_obj(json_data, (..., *path, lambda _, v: v['main_url'])):
                yield {
                    # 'url': base64.b64decode(media['main_url']).decode(),
                    'url': self._aes_decrypt(media['main_url']),
                    'width': int_or_none(media.get('vwidth')),
                    'height': int_or_none(media.get('vheight')),
                    'fps': int_or_none(media.get('fps')),
                    'vcodec': media.get('codec_type'),
                    'format_id': str_or_none(media.get('quality_type')),
                    'filesize': int_or_none(media.get('size')),
                    'ext': 'mp4',
                    **override,
                }
    
    def _aes_decrypt(self,  data: str , ptk) -> str:
        # from Crypto.Cipher import AES
        # from Crypto.Util.Padding import unpad
        # data = base64.b64decode(data)
        # key = ptk.encode()
        # iv = key[:16]

        # # mode 为 CBC、pad 为 PKcs7
        # cipher = AES.new(key, AES.MODE_CBC, iv)
        # res = cipher.decrypt(data)
        # res = unpad(res, AES.block_size)
        # res = base64.b64decode(res).decode()
        # return res
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        data = base64.b64decode(data)
        key = ptk.encode()
        iv = key[:16]

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(data) + decryptor.finalize()
        
        # # 去除 PKcs7 填充
        # unpadder = cryptography.hazmat.primitives.padding.PKCS7(algorithms.AES.block_size).unpadder()
        # unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
        # 使用 PKCS7 填充进行解除填充
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
        
        res = base64.b64decode(unpadded_data).decode()
        return res

    def search_key_in_json(self,data, search_key):
        if isinstance(data, dict):
            if search_key in data:
                return data[search_key]
            for key, value in data.items():
                result = self.search_key_in_json(value, search_key)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self.search_key_in_json(item, search_key)
                if result is not None:
                    return result
        return None
    
    def _real_extract(self, url):
        video_data = None
        import json
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_data = self._get_json_data(webpage, video_id)['anyVideo']['gidInformation']['packerData']['video']
        # print(json_data)
        # json.dump(json_data, open("xigua_before.json","w"))
        

        videoResource = json_data.get('videoResource')
        dash = videoResource['dash'] 
        video_list = self.search_key_in_json(dash,'dynamic_video_list')
        # print(videoResource['normal'])
        # dash = videoResource['normal'] 
        # video_list = list(dash['video_list'].values())
        if dash == None or dash == {}:
            print("dash in normal")
            dash = videoResource['normal'] 

        # print(list(dash['video_list'].values()))
        if video_list == None or video_list == []:
            print("no dynamic video list")
            video_list = list(dash['video_list'].values())
        # dash = videoResource.get('normal')
        ptk = dash.get('ptk')
        
        # ext': 'mp4',
        # video_data =next((obj for obj in video_list ), list(video_list )[len(video_list  )- 1])
        video_data = min(video_list, key=lambda x: x['quality_type'])
        
        main_url  = video_data['main_url']
        # main_url  = video_data['backup_url_1']
        dec_url =  self._aes_decrypt(main_url,ptk)
        print([self._aes_decrypt(one["main_url"],ptk) for one in video_list])
        video_data['url'] = dec_url
        video_data['ext'] ='mp4'
        # self.ptk = ptk
        # print(self.ptk)
        # formats = list(self._media_selector(json_data.get('videoResource')))
        formats = [video_data]
        print(formats)
        # json.dump(formats, open("xigua.json","w"))
        return {
            'id': video_id,
            'title': json_data.get('title'),
            'description': json_data.get('video_abstract'),
            'formats': formats,
            'like_count': json_data.get('video_like_count'),
            'duration': int_or_none(json_data.get('duration')),
            'tags': [json_data.get('tag')],
            'uploader_id': traverse_obj(json_data, ('user_info', 'user_id')),
            'uploader': traverse_obj(json_data, ('user_info', 'name')),
            'view_count': json_data.get('video_watch_count'),
            'dislike_count': json_data.get('video_unlike_count'),
            'timestamp': int_or_none(json_data.get('video_publish_time')),
        }
