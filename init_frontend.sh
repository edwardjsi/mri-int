#!/bin/bash
# Using create-vite@5 because Node 18.19.1 is not compatible with create-vite@latest (Vite 8)
npx -y create-vite@5 frontend --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
