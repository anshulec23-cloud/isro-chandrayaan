# Lunar Operations Command Design System

## 1. Overview
The **Lunar Operations Command** is the official design system for the LUMEN project frontend. It employs a **Spatial Minimalism** philosophy, emulating the dark-room environments of scientific instruments. The design is utilitarian, stark, and highly legible under various lighting conditions, specifically optimized for long-duration operation and technical monitoring.

## 2. Design Philosophy

**Spatial Minimalism** - dark-room philosophy for scientific instruments:
- **Thin-Film UI:** 1px strokes for boundaries, no shadows.
- **Wireframe Motifs:** Vector paths and reticles for data visualization.
- **Glass HUDs:** Translucent overlays with `backdrop-blur: 20px`.
- **Atmosphere:** Astronomical Dark spectrum.
- **Geometry:** Sharp corners (0px radius) - strictly orthogonal.
- **Accents:** 45-degree clipped corners for decorative elements.
- **Spacing:** 4px baseline grid. Minimum 24px internal padding for spatial separation.
- **Modularity:** Modular panels with 1px borders.

## 3. Color System

The color palette is meticulously constructed for high contrast against a dark background, prioritizing readability for critical telemetry and mapping data.

### Core Surfaces
| Token | Hex | Usage |
|-------|-----|-------|
| `surface` | `#131316` | Main background for UI components |
| `surface-dim` | `#131316` | Dimmed surface areas |
| `surface-bright` | `#3a393b` | Highlighted surface areas |
| `surface-container-lowest` | `#0e0e10` | Deepest background layer |
| `surface-container-low` | `#1c1b1e` | Secondary background layer |
| `surface-container` | `#201f22` | Primary container background |
| `surface-container-high` | `#2a2a2c` | Elevated container background |
| `surface-container-highest` | `#353437` | Highest elevation container |

### Text & Icons on Surfaces
| Token | Hex | Usage |
|-------|-----|-------|
| `on-surface` | `#e5e1e5` | Primary text and icons |
| `on-surface-variant` | `#d8c3ad` | Secondary text and icons |
| `inverse-surface` | `#e5e1e5` | Inverted surface backgrounds |
| `inverse-on-surface` | `#313033` | Text on inverted surfaces |

### Borders & Outlines
| Token | Hex | Usage |
|-------|-----|-------|
| `outline` | `#a08e7a` | Primary 1px borders |
| `outline-variant` | `#534434` | Subtle borders and dividers |

### Accents (Amber/Primary)
| Token | Hex | Usage |
|-------|-----|-------|
| `surface-tint` | `#ffb95f` | Surface tinting for accents |
| `primary` | `#ffc174` | Main interactive elements, highlights |
| `on-primary` | `#472a00` | Text/icons on primary color |
| `primary-container` | `#f59e0b` | Accent containers, active states |
| `on-primary-container` | `#613b00` | Text/icons on accent containers |
| `inverse-primary` | `#855300` | Inverted primary color |

### Secondary & Tertiary Data
| Token | Hex | Usage |
|-------|-----|-------|
| `secondary` | `#c7c6cb` | Secondary data points |
| `on-secondary` | `#2f3035` | Text on secondary |
| `secondary-container` | `#46464b` | Secondary metric backgrounds |
| `on-secondary-container` | `#b5b4ba` | Text on secondary metric backgrounds |
| `tertiary` | `#cbccd5` | Tertiary data points |
| `on-tertiary` | `#2e3038` | Text on tertiary |
| `tertiary-container` | `#b0b0ba` | Tertiary metric backgrounds |
| `on-tertiary-container` | `#42434b` | Text on tertiary metric backgrounds |

### Status (Error)
| Token | Hex | Usage |
|-------|-----|-------|
| `error` | `#ffb4ab` | Critical errors, warnings |
| `on-error` | `#690005` | Text on error surfaces |
| `error-container` | `#93000a` | Background for error sections |
| `on-error-container` | `#ffdad6` | Text within error containers |

### Global Background
| Token | Hex | Usage |
|-------|-----|-------|
| `background` | `#131316` | Application root background |
| `on-background` | `#e5e1e5` | Base text color |

## 4. Typography

The typographic system utilizes a combination of Space Grotesk for display, Geist for body text, and JetBrains Mono for technical data.

- **Display Large**: `Space Grotesk`, 48px, Weight: 300, Line-height: 1.1, Letter-spacing: -0.02em
- **Headline Medium**: `Space Grotesk`, 32px, Weight: 400, Line-height: 1.2
- **Body Base**: `Geist`, 16px, Weight: 400, Line-height: 1.6
- **Telemetry Data**: `JetBrains Mono`, 14px, Weight: 500, Line-height: 1.4, Letter-spacing: 0.05em
- **Label XS**: `JetBrains Mono`, 11px, Weight: 700, Line-height: 1

## 5. Spacing System

Based on a strict 4px baseline grid.
- **Micro**: 4px, 8px
- **Standard**: 12px, 16px, 20px
- **Macro**: 24px (minimum internal padding for modules), 32px, 48px, 64px

## 6. Component Library

### Buttons
- **Style**: Sharp-edged (0px radius).
- **Default State**: 1px amber (`primary`) border, transparent fill.
- **Hover/Active State**: Solid `primary` fill, `on-primary` text.
- **Text**: Label XS typography.

### Telemetry Chips
- **Layout**: Inline flex, 4px padding.
- **Typography**: Telemetry Data (JetBrains Mono).
- **Background**: Dim background (`surface-container`).
- **Indicator**: Circular status dot (2px to 4px) indicating system health.

### Input Fields
- **Border**: Bottom-border only (1px `outline`), no side or top borders.
- **Labels**: `Label XS` floating above or inline.
- **Focus State**: Bottom border highlights to `primary`.

### Data Cards
- **Structure**: Modular panels.
- **Border**: 1px solid `outline` or `surface-container-high`.
- **Background**: Solid `surface-container-low`.
- **Detail**: Module ID in the top-right corner (Label XS).
- **Padding**: Minimum 24px internal padding.

### Crosshair/Reticles
- **Use Case**: Map focal points and target acquisition.
- **Animation**: Subtle pulse animation on active targets.
- **Style**: Vector SVG paths, 1px stroke, no fill.

### Technical Lists
- **Dividers**: Dashed 1px lines (`outline-variant`) between list items.
- **Layout**: Flexbox rows, tightly packed but legible.

## 7. Application Architecture & Screens

1. **Mapping/Geometry** (Primary): Three-panel layout (Source Observation, Acquisition Geometry 3D Viz, Reference Observation).
2. **Telemetry**: Real-time sensor data monitoring in dense data grids.
3. **Pipeline**: Registration pipeline status and control with step-by-step visualizers.
4. **Datasets**: Browse and manage PRADAN data through data tables.
5. **Metrics**: Evaluation results visualization with wireframe graphs.
6. **Alerts**: System notifications and warnings in persistent HUD elements.
7. **Logs**: Processing logs and audit trail in raw terminal-style output.

## 8. Responsive Behavior

- **Desktop (>= 1024px)**: Multi-column dashboard layout with persistent left/right side navigation and deep module nesting.
- **Mobile (< 1024px)**: Stacked modules vertically. Navigation collapses into a bottom bar. Contextual data moves into collapsible drawers.

## 9. Accessibility Considerations
- Contrast ratios strictly adhere to WCAG AAA standards for critical telemetry (using amber on dark grey/black).
- Monospaced fonts for numerical data prevent layout shifts during real-time updates.
- Focus states are highly visible using 1px solid amber borders.

## 10. Reference Implementation: Mapping/Geometry Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LUMEN - Mapping/Geometry</title>
    <style>
        :root {
            --surface: #131316;
            --surface-container-low: #1c1b1e;
            --outline: #a08e7a;
            --outline-variant: #534434;
            --primary: #ffc174;
            --on-primary: #472a00;
            --on-surface: #e5e1e5;
            --telemetry-font: 'JetBrains Mono', monospace;
            --body-font: 'Geist', sans-serif;
            --display-font: 'Space Grotesk', sans-serif;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background-color: var(--surface);
            color: var(--on-surface);
            font-family: var(--body-font);
            display: flex;
            height: 100vh;
            overflow: hidden;
            font-size: 16px;
            line-height: 1.6;
        }

        .hud-overlay {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            box-shadow: inset 0 0 100px rgba(0,0,0,0.8);
            z-index: 100;
        }

        nav.sidebar {
            width: 240px;
            border-right: 1px solid var(--outline-variant);
            display: flex;
            flex-direction: column;
            padding: 24px;
        }

        .brand {
            font-family: var(--display-font);
            font-size: 32px;
            font-weight: 300;
            letter-spacing: -0.02em;
            margin-bottom: 48px;
            color: var(--primary);
        }

        .nav-item {
            font-family: var(--telemetry-font);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 12px 0;
            border-bottom: 1px dashed var(--outline-variant);
            cursor: pointer;
            color: var(--on-surface);
        }
        .nav-item.active { color: var(--primary); }

        main.dashboard {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 1.5fr 1fr;
            gap: 24px;
            padding: 24px;
        }

        .panel {
            background-color: var(--surface-container-low);
            border: 1px solid var(--outline);
            padding: 24px;
            position: relative;
            display: flex;
            flex-direction: column;
        }

        .panel-id {
            position: absolute;
            top: 8px;
            right: 8px;
            font-family: var(--telemetry-font);
            font-size: 11px;
            color: var(--outline);
        }

        .panel-title {
            font-family: var(--telemetry-font);
            font-size: 14px;
            letter-spacing: 0.05em;
            margin-bottom: 24px;
            color: var(--primary);
            text-transform: uppercase;
        }

        .wireframe-view {
            flex: 1;
            border: 1px dashed var(--outline-variant);
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .reticle {
            width: 40px;
            height: 40px;
            border: 1px solid var(--primary);
            position: absolute;
        }
        .reticle::before, .reticle::after {
            content: '';
            position: absolute;
            background: var(--primary);
        }
        .reticle::before { width: 1px; height: 100%; left: 50%; top: 0; }
        .reticle::after { height: 1px; width: 100%; top: 50%; left: 0; }

        .data-list {
            list-style: none;
            margin-top: 16px;
        }

        .data-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px dashed var(--outline-variant);
            font-family: var(--telemetry-font);
            font-size: 14px;
        }

        .btn {
            background: transparent;
            border: 1px solid var(--primary);
            color: var(--primary);
            padding: 8px 16px;
            font-family: var(--telemetry-font);
            font-size: 11px;
            text-transform: uppercase;
            cursor: pointer;
            margin-top: 24px;
        }
        .btn:hover {
            background: var(--primary);
            color: var(--on-primary);
        }
    </style>
</head>
<body>
    <div class="hud-overlay"></div>
    
    <nav class="sidebar">
        <div class="brand">LUMEN</div>
        <div class="nav-item active">01. Mapping/Geometry</div>
        <div class="nav-item">02. Telemetry</div>
        <div class="nav-item">03. Pipeline</div>
        <div class="nav-item">04. Datasets</div>
    </nav>

    <main class="dashboard">
        <!-- Source Observation Panel -->
        <section class="panel">
            <div class="panel-id">MOD-A1</div>
            <h2 class="panel-title">Source Observation</h2>
            <div class="wireframe-view">
                <div class="reticle"></div>
                <!-- Canvas or Image would go here -->
            </div>
            <ul class="data-list">
                <li class="data-row"><span>INCIDENCE</span><span>42.5°</span></li>
                <li class="data-row"><span>EMISSION</span><span>12.1°</span></li>
                <li class="data-row"><span>PHASE</span><span>54.6°</span></li>
            </ul>
        </section>

        <!-- 3D Geometry Panel -->
        <section class="panel">
            <div class="panel-id">MOD-B1</div>
            <h2 class="panel-title">Acquisition Geometry</h2>
            <div class="wireframe-view" style="border: 1px solid var(--primary);">
                <!-- 3D WebGL context goes here -->
                <div style="font-family: 'Space Grotesk'; font-size: 48px; opacity: 0.2;">3D VIZ</div>
            </div>
            <button class="btn">Recalibrate Vector</button>
        </section>

        <!-- Reference Observation Panel -->
        <section class="panel">
            <div class="panel-id">MOD-C1</div>
            <h2 class="panel-title">Reference Observation</h2>
            <div class="wireframe-view">
                <div class="reticle" style="transform: scale(0.5); top: 20%; left: 30%;"></div>
            </div>
            <ul class="data-list">
                <li class="data-row"><span>RESOLUTION</span><span>0.5m/px</span></li>
                <li class="data-row"><span>SUN_AZIMUTH</span><span>112.4°</span></li>
            </ul>
        </section>
    </main>
</body>
</html>
```
