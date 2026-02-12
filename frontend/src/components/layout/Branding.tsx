import React from 'react'
import { Plus } from 'lucide-react'

// TODO: Измените название клиники здесь
export const CLINIC_NAME = 'Я - Здоров!'

export const Branding: React.FC = () => {
  return (
    <div className="flex items-center gap-2">
      {/* 
        TODO: Чтобы добавить свой логотип:
        1. Положите файл логотипа (например, logo.png) в папку frontend/public/
        2. Раскомментируйте строку <img> ниже и поменяйте src="/logo.png" на ваше имя файла
        3. Удалите или закомментируйте блок <div> с иконкой Plus ниже
      */}
      
      <img src="/images/logo2.png" alt="Логотип" className="h-10 w-auto object-contain" />
    </div>
  )
}
