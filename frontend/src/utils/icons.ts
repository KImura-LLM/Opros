/**
 * Утилита для получения иконок Lucide по имени
 */

import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Brain,
  CheckCircle,
  Clipboard,
  ClipboardCheck,
  Droplet,
  Heart,
  HelpCircle,
  Thermometer,
  Utensils,
  Wind,
  type LucideIcon,
} from 'lucide-react'

const iconMap: Record<string, LucideIcon> = {
  activity: Activity,
  'alert-circle': AlertCircle,
  'alert-triangle': AlertTriangle,
  brain: Brain,
  'check-circle': CheckCircle,
  clipboard: Clipboard,
  'clipboard-check': ClipboardCheck,
  droplet: Droplet,
  heart: Heart,
  'help-circle': HelpCircle,
  thermometer: Thermometer,
  utensils: Utensils,
  wind: Wind,
}

export function getIcon(name: string): LucideIcon | null {
  return iconMap[name] || null
}
