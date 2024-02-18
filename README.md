# 文灵 (Wen Ling)

Inspired by the ingenuity of 仓颉 (Cang Jie), an ancient Chinese figure celebrated for inventing Chinese characters, 文灵 (Wen Ling) embodies the spirit of innovative communication in the digital age. Just as Cang Jie's invention brought forth a new era in written language, 文灵 aims to revolutionize the way we collect, assemble, and disseminate information online. This platform is designed to automate the collection and archiving of online information, intelligently assemble articles, and publish them seamlessly across a wide range of social media platforms.

## About This Repository

文灵 (Wen Ling) is an AI-powered content generation and distribution system tailored for both Chinese and English social media landscapes. This repository is the hub for the system's core engine, integrating cutting-edge AI to streamline content creation and publication.

## Key Features

Automated Information Collection: Efficiently gathers and archives relevant online information.
Intelligent Article Assembly: Utilizes AI algorithms to assemble collected information into coherent and engaging articles.
Multi-platform Publishing: Capable of publishing content across various platforms including 小红书, B 站 (Bilibili), 知乎 (Zhihu), 微信公众号 (WeChat Official Accounts), Substack, Medium, Facebook, and Instagram.
Cross-language Support: Designed to cater to both Chinese and English social media platforms, maximizing global reach and engagement.
Customization and User Preferences: Allows for tailored content strategies based on user preferences and platform-specific nuances.

# Setup
## Build and run
```
docker-compose -f ./docker-compose.yml up --build wenling
```

# Deployment
## Local test of Railway.app deployment
See https://docs.railway.app/guides/cli#local-development.

# Local test of web service

## Start the web service

```
uvicorn wenling.web_service:app --reload --log-level debug
```


## Cleanup docker images not used
```
docker rm $(docker ps -a -q) ; docker images | grep '<none>' | awk '{print $3}' | xargs docker rmi
```