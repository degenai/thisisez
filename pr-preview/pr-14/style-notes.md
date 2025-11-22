# Cyberpunk Terminal Aesthetic Guide

## Core Design Philosophy
**"Hacker Terminal meets Financial Analysis"** - Authentic retro-computing aesthetic with modern data visualization. Think 1980s terminal screens analyzing 2020s financial collapse.

## Color Palette
```css
Background:     #000 (pure black)
Primary text:   #0f0 (bright green) 
Commands:       #0ff (cyan)
Prompts:        #ff0 (yellow)
Errors:         #f00 (red)
Warnings:       #ff0 (yellow)
Critical:       #f0f (magenta) - reserved for urgent alerts
Links:          #0ff (cyan)
```

## Typography
- **Font:** JetBrains Mono (primary), Courier New (fallback)
- **Size:** 14px base, 12px for small elements, 10px for ASCII art
- **Weight:** Normal for content, bold for headers/critical alerts
- **Text shadow:** `0 0 5px #0f0` for authentic CRT glow effect

## Visual Effects
### Animations
- **Flicker:** Subtle opacity animation (0.98-1.0) for system messages
- **Blink:** 0.5s on/off for critical alerts  
- **Cursor:** 1s blink cycle with block character
- **Text typing:** 20ms delay per character for dramatic reveals

### ASCII Elements
- **Bars:** Use `█▓▒░` for progress/data visualization
- **EQ Style:** `▁▂▃▄▅▆▇█` for audio-visualizer-like charts
- **Borders:** `═══` for section dividers
- **Indicators:** `⚠🔥` for warnings (sparingly)

## Content Structure
### Headers
```
[!] SYSTEM: Status messages
[!] WARNING: Yellow alerts  
[!] CRITICAL: Magenta emergencies
[*] Loading/processing indicators
```

### Command Interface
```
root@capitalism:~$ [user input]
thisisez:~$ [alternative prompt]
```

### Data Presentation
- **Static data:** Clean, factual presentation
- **Avoid fake "real-time"** for quarterly/sporadic data
- **Use animation only when it adds value**
- **Progress bars:** Show actual progress, not meaningless fluctuation

## Interactive Elements
### Navigation
- **Back links:** Fixed position, subtle styling
- **Hover states:** Minimal color shifts, no fancy transitions
- **Focus:** Maintain terminal aesthetic

### Input Fields
- **Transparent background**
- **No borders** (invisible until typed in)
- **Inherit terminal font/color**
- **Auto-focus** for immediate interaction

## Layout Principles
- **Max width:** 900px for readability
- **Centered content** with black margins
- **Minimal padding:** 20px standard
- **Vertical rhythm:** Consistent spacing between sections
- **Mobile:** Preserve aesthetic, reduce font sizes if needed

## Content Voice
- **Technical but accessible**
- **Dark humor about financial collapse**
- **Marxist economic terminology where relevant**
- **Authentic hacker/terminal language**
- **No corporate marketing speak**

## What to Avoid
❌ **Rounded corners** (destroys retro feel)  
❌ **Gradients** (terminals are flat)  
❌ **Modern web fonts** (stick to monospace)  
❌ **Bright backgrounds** (terminals are dark)  
❌ **Fake real-time data** (be honest about data cadence)  
❌ **Excessive animations** (subtle is better)  
❌ **Corporate color schemes** (green/black is the way)  

## Inspiration Sources
- 1980s terminal computers
- Hacker movies (Matrix, WarGames)
- Audio spectrum analyzers
- Financial terminal software (Bloomberg Terminal)
- Retro computing aesthetics

## Implementation Notes
- **Performance:** Keep animations lightweight
- **Accessibility:** Maintain contrast ratios
- **Compatibility:** Test on different screen sizes
- **Loading:** Progressive enhancement, content first

---

*"The aesthetic should feel like a financial analyst hacked into the mainframe to reveal the truth about market collapse."*
