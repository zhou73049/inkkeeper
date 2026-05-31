# InkKeeper — 打印机喷头自动保养程序

定时自动打印保养图片，防止喷墨打印机喷头堵塞。支持 Web 管理界面。

## 功能

- 定时自动打印（按星期 + 时间精确设置）
- 手动一键打印
- 多图片管理（上传/删除/启用/禁用）
- 打印日志记录
- Web 管理界面（深色主题）
- 支持 CUPS / 网络直连 / 自定义脚本

## 支持设备

- iStoreOS / OpenWrt 路由器
- 爱快 (iKuai) 路由
- 飞牛 NAS
- 任何有 Docker 的 Linux 设备

 ## 使用方法
1. 「图片管理」上传保养测试图
2. 「定时任务」设置自动打印计划
3. 点「执行」立即手动打印

## 推荐保养图片
- CMYK 四色大色块图
- 彩虹渐变条
- 黑色满幅图
- 喷嘴检查图案

## 快速部署

1. 修改配置
编辑 `docker-compose.yml`，修改以下内容：
- `PRINTER_NAME` — 你的打印机型号
- `PRINTER_IP` — 你的打印机 IP 地址
- `WEB_PORT` — Web 端口（默认 15000）

2. 启动
docker compose up -d --build

text
text

3. 访问
浏览器打开 `http://你的设备IP:15000`

## 常用命令
docker logs inkkeeper --tail 50 # 查看日志
docker restart inkkeeper # 重启
docker stop inkkeeper # 停止
# -
设置打印机自动打印，从而保证喷头不堵塞。适用于家里有喷墨打印机 ，但是打印较少，导致喷头易堵。此程序为AI编写，本人不懂代码，任何问题反馈给我，我都不能及时解决！！
