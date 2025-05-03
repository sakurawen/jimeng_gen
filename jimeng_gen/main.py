import os
import base64
import time
import requests
from volcengine.visual.VisualService import VisualService
from dotenv import load_dotenv

load_dotenv()

class VideoGenerator:
    def __init__(self, ak, sk, images_dir='images'):
        """初始化视频生成器
        
        Args:
            ak: Access Key
            sk: Secret Key
            images_dir: 图片目录路径，默认为'images'
        """
        self.visual_service = VisualService()
        self.visual_service.set_ak(ak)
        self.visual_service.set_sk(sk)
        self.images_dir = images_dir
        self.image_extensions = ('.jpg', '.jpeg')

    def process_image(self, filename):
        """处理单张图片并发送请求
        
        Args:
            filename: 图片文件名
        
        Returns:
            API响应结果
        """
        try:
            file_path = os.path.join(self.images_dir, filename)
            with open(file_path, 'rb') as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                create_form = {
                    'prompt':"人像简单动一下眨一眨眼睛，只要大头照",
                    "req_key": "jimeng_vgfm_i2v_l20",
                    'binary_data_base64': [image_base64],
                }
                create_resp = self.visual_service.cv_sync2async_submit_task(create_form)
                if not create_resp['data'] or not create_resp['data']['task_id']:
                    return None
                task_id = create_resp['data']['task_id']
                print(f"Processing {filename}:")
                print(f'{create_resp=}')
                print("-" * 50)
                query_form={
                    'req_key':"jimeng_vgfm_i2v_l20",
                    'task_id':task_id
                }
                max_retries = 60
                for i in range(max_retries):
                    query_resp = self.visual_service.cv_sync2async_get_result(query_form)
                    if query_resp.get('data',{}).get('status')=='done':
                        print("-" * 50)
                        video_url = query_resp['data'].get('video_url')
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
                        return query_resp
                    else:
                        print(f"{filename}视频结果查询中, 重试第{i+1}次...")
                        time.sleep(5)

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            return None

    def generate_video_from_images(self):
        """从图片目录生成视频
        
        Returns:
            所有图片处理的结果列表
        """
        for filename in os.listdir(self.images_dir):
            if filename.lower().endswith(self.image_extensions):
                 self.process_image(filename)
                    


if __name__ == '__main__':
    # 配置
    AK = os.getenv('access_key')
    SK = os.getenv('sceret_key')
    
    # 创建视频生成器
    generator = VideoGenerator(AK, SK)
    
    # 生成视频
    results = generator.generate_video_from_images()
 
