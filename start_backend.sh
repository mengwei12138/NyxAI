#!/bin/bash
cd /Users/songmowei/opcode/NyxAI_Tg/backend
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000
