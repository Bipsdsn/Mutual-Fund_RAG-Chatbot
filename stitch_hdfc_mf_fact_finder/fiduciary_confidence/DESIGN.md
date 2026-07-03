---
name: Fiduciary Confidence
colors:
  surface: '#fbf8fc'
  surface-dim: '#dbd9dd'
  surface-bright: '#fbf8fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f7'
  surface-container: '#efedf1'
  surface-container-high: '#e9e7eb'
  surface-container-highest: '#e4e2e5'
  on-surface: '#1b1b1e'
  on-surface-variant: '#44464e'
  inverse-surface: '#303033'
  inverse-on-surface: '#f2f0f4'
  outline: '#75777f'
  outline-variant: '#c5c6cf'
  surface-tint: '#4c5e86'
  primary: '#00081e'
  on-primary: '#ffffff'
  primary-container: '#0a1f44'
  on-primary-container: '#7687b2'
  inverse-primary: '#b4c6f4'
  secondary: '#006a66'
  on-secondary: '#ffffff'
  secondary-container: '#7df6ef'
  on-secondary-container: '#00716d'
  tertiary: '#150500'
  on-tertiary: '#ffffff'
  tertiary-container: '#391700'
  on-tertiary-container: '#b37c59'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d9e2ff'
  primary-fixed-dim: '#b4c6f4'
  on-primary-fixed: '#041a3f'
  on-primary-fixed-variant: '#34466d'
  secondary-fixed: '#7df6ef'
  secondary-fixed-dim: '#5ed9d3'
  on-secondary-fixed: '#00201f'
  on-secondary-fixed-variant: '#00504d'
  tertiary-fixed: '#ffdbc7'
  tertiary-fixed-dim: '#f8b992'
  on-tertiary-fixed: '#311300'
  on-tertiary-fixed-variant: '#673c1e'
  background: '#fbf8fc'
  on-background: '#1b1b1e'
  surface-variant: '#e4e2e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
  headline-md-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.3'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  container-max: 1200px
  chat-max-width: 800px
---

## Brand & Style
The design system is engineered to project a sense of institutional stability, technical precision, and modern accessibility. As a consumer-fintech interface, the aesthetic balances the gravitas of a traditional financial institution with the agility of a digital-first assistant.

The visual style is **Corporate Modern with a focus on Clarity**. It utilizes a structured layout, purposeful whitespace, and a high-contrast color palette to ensure that complex financial information is digestible and authoritative. The emotional response should be one of reassurance—users should feel that their inquiries are being handled by a reliable, expert system that values transparency over flashiness.

## Colors
The palette is rooted in a deep navy blue, symbolizing trust and expertise. A secondary teal accent provides a "digital-native" feel, used sparingly for calls to action and success states.

- **Primary:** Deep Navy (#0a1f44). Used for headers, primary actions, and brand-heavy elements. A gradient transition to #1e4fa3 is applied to large surfaces like the header to add depth.
- **Accent:** Fresh Teal (#0ea5a0). Reserved for interaction highlights, active pill badges, and key icons.
- **Backgrounds:** A soft neutral (#f5f7fb) distinguishes the application canvas from content surfaces.
- **Surfaces:** Pure white (#ffffff) is used for cards and chat bubbles to maximize legibility and create a "lifted" feel against the neutral background.

## Typography
Inter is the sole typeface for this design system, chosen for its exceptional legibility in data-dense environments.

- **Headlines:** Use Bold (700) or Semi-Bold (600) weights with tighter letter spacing to create a strong visual anchor.
- **Body:** Standard body text uses a 1.6 line-height ratio to ensure that long-form FAQ answers are readable and don't feel "crowded."
- **Labels:** Used for metadata, status pills, and small buttons. These are often slightly tracked out for clarity at small sizes.

## Layout & Spacing
The layout follows a **Fixed-Width Centered** model for the chat interface to maintain focus and readability.

- **Grid:** A 12-column grid is used for dashboard views, while the FAQ Assistant interface is constrained to a central 800px column.
- **Gutter & Margins:** 24px gutters on desktop, reduced to 16px on mobile.
- **The "Safe Zone":** The sticky bottom composer bar includes a 48px vertical safety margin to prevent content from being obscured during scroll.
- **Mobile Adaption:** On screens smaller than 768px, side margins are reduced to 16px and typography scales down according to the mobile tokens.

## Elevation & Depth
Depth is created through a combination of **Tonal Layering** and **Ambient Shadows**.

- **Level 0 (Background):** The soft neutral (#f5f7fb) floor.
- **Level 1 (Cards/Bubbles):** White surfaces with a very soft, diffused shadow (0px 4px 20px rgba(10, 31, 68, 0.05)).
- **Level 2 (Interactive):** Elements like active input fields or hovered cards gain a more pronounced shadow (0px 8px 30px rgba(10, 31, 68, 0.08)) and a 1px border using the primary color at 10% opacity.
- **The Header:** Stays fixed at the top with a subtle bottom shadow to indicate it sits above the scrolling content.

## Shapes
The shape language is "Friendly Professional." It avoids the clinical feel of sharp corners while maintaining enough structure to feel serious.

- **Standard Elements:** Buttons, cards, and input fields use a **12px (rounded-lg)** radius.
- **Chat Bubbles:** Use a **16px (rounded-xl)** radius. User bubbles have the bottom-right corner squared off, while Assistant bubbles have the bottom-left corner squared.
- **Pills:** Status badges and category tags use a fully rounded/pill shape (999px).

## Components
Consistent component behavior ensures a predictable user experience.

- **Sticky Header:** Uses the primary gradient. Icons and text should be white. Height is fixed at 72px.
- **Chat Bubbles:**
    - *User:* Gradient background (Primary to Secondary), white text, right-aligned.
    - *Assistant:* White background, Primary Navy text, 1px soft border (#e1e8f0), left-aligned. Includes a small teal icon of the brand mark as an avatar.
- **Composer Bar:** A white, sticky container at the bottom with a 1px top border. The input field inside should have a 24px radius and a prominent "Send" button using the teal accent.
- **Buttons:**
    - *Primary:* Solid Teal with white text.
    - *Secondary:* Ghost style with a Primary Navy border and text.
- **Pill Badges:** Low-saturation backgrounds with high-saturation text (e.g., a light teal background for a "Verified" status).
- **Motion:** 
    - *Entrances:* Assistant messages should "fade-up" with a 200ms duration and a slight spring.
    - *Hover:* Interactive cards should lift -2px on the Y-axis.