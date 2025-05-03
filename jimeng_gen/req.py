import json
import sys
import os
import base64
import datetime
import hashlib
import hmac
import time
import requests
from dotenv import load_dotenv

load_dotenv()

method = 'POST'
host = 'visual.volcengineapi.com'
region = 'cn-north-1'
endpoint = 'https://visual.volcengineapi.com'
service = 'cv'

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(key.encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'request')
    return kSigning

def formatQuery(parameters):
    request_parameters_init = ''
    for key in sorted(parameters):
        request_parameters_init += key + '=' + parameters[key] + '&'
    request_parameters = request_parameters_init[:-1]
    return request_parameters

def signV4Request(access_key, secret_key, service, req_query, req_body):
    if access_key is None or secret_key is None:
        print('No access key is available.')
        sys.exit()

    t = datetime.datetime.utcnow()
    current_date = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')  # Date w/o time, used in credential scope
    canonical_uri = '/'
    canonical_querystring = req_query
    signed_headers = 'content-type;host;x-content-sha256;x-date'
    payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
    content_type = 'application/json'
    canonical_headers = 'content-type:' + content_type + '\n' + 'host:' + host + \
        '\n' + 'x-content-sha256:' + payload_hash + \
        '\n' + 'x-date:' + current_date + '\n'
    canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + \
        '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
    # print(canonical_request)
    algorithm = 'HMAC-SHA256'
    credential_scope = datestamp + '/' + region + '/' + service + '/' + 'request'
    string_to_sign = algorithm + '\n' + current_date + '\n' + credential_scope + '\n' + hashlib.sha256(
        canonical_request.encode('utf-8')).hexdigest()
    # print(string_to_sign)
    signing_key = getSignatureKey(secret_key, datestamp, region, service)
    # print(signing_key)
    signature = hmac.new(signing_key, (string_to_sign).encode(
        'utf-8'), hashlib.sha256).hexdigest()
    # print(signature)
    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
        credential_scope + ', ' + 'SignedHeaders=' + \
        signed_headers + ', ' + 'Signature=' + signature
    headers = {'X-Date': current_date,
               'Authorization': authorization_header,
               'X-Content-Sha256': payload_hash,
               'Content-Type': content_type
               }
    request_url = endpoint + '?' + canonical_querystring

    try:
        r = requests.post(request_url, headers=headers, data=req_body)
    except Exception as err:
        print(f'error occurred: {err}')
        raise
    else:
        return r


class VideoGenerator:
  def __init__(self,ak,sk,images_dir='images'):
      self.ak = ak
      self.sk = sk
      self.images_dir = images_dir
      self.image_extensions = ('.jpg', '.jpeg')

  def process_image(self,filename):
    try:
      file_path = os.path.join(self.images_dir,filename)
      with open(file_path,'rb') as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        create_body = {
          'prompt':"人像简单动一下眨一眨眼睛，只要大头照",
          "req_key": "jimeng_vgfm_i2v_l20",
          'binary_data_base64': [image_base64],
        }
        create_params = {
          "Action":"CVSync2AsyncSubmitTask",
          "Version":"2022-08-31"
        }
        formatted_create_params  = formatQuery(create_params)
        formatted_create_body = json.dumps(create_body)
        create_resp = signV4Request(self.ak,self.sk,service,formatted_create_params,formatted_create_body)
        create_resp_json = create_resp.json()
        print(f'{create_resp_json=}')
        if not create_resp_json['data'] or not create_resp_json['data']['task_id']:
            return None
        task_id = create_resp_json['data']['task_id']
        print(f'图{filename=}生视频任务创建成功,{task_id=}')
        query_body = {
            'req_key':"jimeng_vgfm_i2v_l20",
            'task_id':task_id
        }
        query_params = {
            'Action':"CVSync2AsyncGetResult",
            "Version":"2022-08-31"
        }
        formatted_query_body = json.dumps(query_body)
        formatted_query_params = formatQuery(query_params)
        max_retries = 60
        for i in range(max_retries):
            query_resp = signV4Request(self.ak,self.sk,service,formatted_query_params,formatted_query_body)
            query_resp_json = query_resp.json()
            if query_resp_json.get('data',{}).get('status')=='done':
                print("-" * 50)
                video_url = query_resp_json['data'].get('video_url')
                if video_url:
                    response = requests.get(video_url)
                    if response.status_code == 200:
                        os.makedirs('video', exist_ok=True)
                        video_path = os.path.join('video', f"{os.path.splitext(filename)[0]}.mp4")
                        with open(video_path, 'wb') as f:
                            f.write(response.content)
                        print(f"Video saved to {video_path}")
                    else:
                        print(f"Failed to download video for {filename}")
                return query_resp_json
            else:
                print(f"{filename}视频结果查询中, 重试第{i+1}次...")
                time.sleep(5)

    except Exception as e:
      print(f'Error processing {filename}:{str(e)}')
      return None

  def generate_video_from_images(self):
    for filename in os.listdir(self.images_dir):
      if filename.lower().endswith(self.image_extensions):
        self.process_image(filename)

if __name__=='__main__':
  AK = os.getenv('access_key')
  SK = os.getenv('sceret_key')
  generator = VideoGenerator(AK,SK)
  generator.generate_video_from_images()
