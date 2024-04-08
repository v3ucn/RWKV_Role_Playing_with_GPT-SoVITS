@echo off
chcp 65001

call runtime\python.exe webui.py --cuda_on 1

@echo 请按任意键继续
call pause