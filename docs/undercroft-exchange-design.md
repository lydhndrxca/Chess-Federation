# The Undercroft Exchange

## Feature Design Document — Chess Federation

---

## 1. Overview

The Undercroft Exchange is a simulated commodity market embedded within the Chess Federation platform. Players buy and sell Enoch's hoarded trinkets — strange, decaying items scavenged from the abandoned school band room across the street from the sub-basement. Prices fluctuate according to a layered system of hidden forces, creating an experience that mirrors the volatility, pattern-recognition, and emotional swings of real cryptocurrency and stock markets.

The Exchange operates on its own in-game currency ("Dust"), entirely separate from the rating system. It is designed to be exciting, addictive, and deeply thematic — a strange little economy humming beneath the chessboard.

---

## 2. Narrative Context

Enoch has been crossing the street at night. Beneath the abandoned school is a band practice room — waterlogged, mold-streaked, and forgotten. Over time he has hauled crates of decaying instruments, sheet music, and unidentifiable supplies back to his sub-basement. He has catalogued them. He has assigned them value. He insists they are worth something.

The Undercroft Exchange is where players trade these goods. Enoch acts as the sole market maker — you buy from him, you sell back to him. He sets the prices. He takes a cut. He mutters about every transaction. The items are strange. The market is stranger. But the numbers go up and down, and that is all anyone needs.

---

## 3. The Commodities

The Exchange trades in **10 commodity categories**. These are not unique collectibles — they are fungible goods measured in units. A player can hold 14 units of Brass Rot the same way someone holds 14 shares of a stock.

| # | Commodity | Description | Instrument Family |
|---|-----------|-------------|-------------------|
| 1 | **Damp Sheet Music** | Water-stained orchestral scores, ink bleeding between staves. Some pages are fused together. Enoch insists certain compositions are "still alive." | General |
| 2 | **Brass Rot** | Corroded trumpet valves, dented tuba fittings, green-patinated French horn tubing. The oxidation patterns shift depending on what Enoch stores them near. | Brass |
| 3 | **Catgut Coils** | Old violin and cello strings wound into tight spirals. They are not actually made of catgut — or perhaps they are. Enoch will not clarify. Slightly warm to the touch. | Strings |
| 4 | **Reed Mold** | Decomposing clarinet and oboe reeds in various stages of biological rebellion. Some have sprouted. Enoch waters them. | Woodwind |
| 5 | **Rosin Dust** | Powdered violin rosin collected from the floor of the practice room. Stored in unlabeled jars. Smells faintly of pine and something older. | Strings |
| 6 | **Cracked Tailguts** | Snapped tailpiece cords from violins and violas. Enoch keeps them sorted by the sound they made when they broke. | Strings |
| 7 | **Felt Hammers** | Piano hammers in varying states of moth damage. Some still carry the compression marks of the last note they ever played. Enoch claims he can read them. | Percussion / Keys |
| 8 | **Valve Oil** | Ancient, murky bottles of brass instrument lubricant. The viscosity changes with temperature. Some bottles have solidified entirely and are traded as curiosities. | Brass |
| 9 | **Bow Hair** | Bundles of horsehair harvested from broken violin and cello bows. Origin uncertain. Enoch says the horse is "still around." | Strings |
| 10 | **Metronome Teeth** | Tiny brass gears and escapement components from broken metronomes. They tick faintly when stacked. Enoch finds this soothing. | Percussion / Mechanical |

### Instrument Family Groupings

These family groupings matter for the Resonance system (see Section 5.3):

- **Strings**: Catgut Coils, Rosin Dust, Cracked Tailguts, Bow Hair
- **Brass**: Brass Rot, Valve Oil
- **Woodwind**: Reed Mold
- **Percussion / Mechanical**: Felt Hammers, Metronome Teeth
- **General**: Damp Sheet Music (weakly linked to all families)

---

## 4. Currency: Dust

The Exchange operates on a currency called **Dust** — fine, unidentifiable particulate that coats everything in Enoch's sub-basement. It is the unit of account for all market transactions.

### 4.1 Earning Dust

Players accumulate Dust through normal site activity:

| Source | Amount | Frequency |
|--------|--------|-----------|
| Daily login | 5 Dust | Once per day |
| Completing any match (win or lose) | 3 Dust | Per match |
| Winning a match | +2 Dust bonus | Per win |
| Completing a Crypt wave | 1 Dust per wave | Per wave cleared |
| Completing a full Crypt run (all 10 waves) | 15 Dust bonus | Per completion |
| Receiving a commendation | 2 Dust | Per commendation |
| Winning an Enoch wager | 3 Dust | Per wager won |

*Note: These values are initial suggestions and should be tuned after observing how quickly players accumulate capital. The goal is that a moderately active player earns roughly 20-30 Dust per day from non-trading activity.*

### 4.2 Dust Is Not Rating

Dust has no direct conversion to rating points. The two economies are deliberately separate. However, future features could bridge them — for example, spending Dust to unlock cosmetic items, or a monthly "auction" where Dust can buy small rating bonuses. This bridge should be introduced later and carefully, to avoid pay-to-win dynamics.

### 4.3 Starting Capital

New players receive **50 Dust** upon first visiting the Exchange. This is enough to make a few trades and learn the system, but not enough to move the market or profit significantly without earning more through gameplay.

---

## 5. The Price Engine

The core design challenge is making prices feel alive — patterned enough that players believe skill matters, chaotic enough that no one can solve it. This is achieved by **layering three independent systems** that interact to produce emergent behavior.

### 5.1 Layer One: The Pipes (Environmental Cycle)

**Concept:** The sub-basement has its own micro-climate. Temperature, humidity, and water levels cycle on slow, overlapping rhythms. These environmental conditions affect different commodities differently.

**Implementation:**

Three hidden environmental variables cycle continuously:

- **Temperature**: Oscillates on a ~60-hour sine wave with ±15% random noise per tick
- **Humidity**: Oscillates on a ~84-hour sine wave (deliberately out of phase with temperature) with ±10% noise
- **Water Level**: Oscillates on a ~108-hour sine wave with ±20% noise and occasional sharp spikes (pipe bursts)

Each commodity has a **sensitivity vector** — how it responds to each environmental variable:

| Commodity | Temperature | Humidity | Water Level |
|-----------|------------|----------|-------------|
| Damp Sheet Music | 0 | −0.3 | −0.5 |
| Brass Rot | +0.2 | −0.4 | −0.2 |
| Catgut Coils | −0.3 | +0.1 | −0.1 |
| Reed Mold | +0.1 | +0.5 | +0.3 |
| Rosin Dust | −0.2 | −0.2 | 0 |
| Cracked Tailguts | −0.4 | 0 | −0.1 |
| Felt Hammers | 0 | −0.3 | −0.4 |
| Valve Oil | −0.5 | +0.1 | 0 |
| Bow Hair | +0.1 | −0.1 | −0.2 |
| Metronome Teeth | 0 | 0 | +0.1 |

*Positive values mean price rises when that variable increases. Negative values mean price falls.*

**Player-facing clues:** Players never see the raw numbers. Instead, Enoch drops hints in the Exchange feed:

- *"The pipes are sweating today."* → Humidity is high
- *"There is frost on the boiler."* → Temperature is low
- *"I can hear water beneath the floor."* → Water level is rising
- *"The air is thick and warm. I do not like it."* → Temperature and humidity both high
- *"Everything is dry. The paper crackles when I breathe near it."* → Humidity is very low

These clues appear 2-4 times per day. Attentive players learn to read them as market signals over time.

**Drift:** Every 2-3 weeks, the sensitivity vectors shift slightly (±0.1 on random axes). This prevents anyone from permanently "solving" the environmental model. The drift is silent — players only notice when their old strategies stop working as well.

### 5.2 Layer Two: The Visitors (Demand Shocks)

**Concept:** Unnamed NPCs periodically visit the sub-basement and affect demand for specific commodities. They are never seen — only referenced through Enoch's cryptic announcements. Each visitor archetype has consistent (but initially unknown) market preferences.

**The Visitor Roster:**

| Visitor | Enoch's Description | Market Effect |
|---------|-------------------|---------------|
| **The Woman from the Third Floor** | *"The woman from the third floor was here again. She touched the strings and left without paying."* | Strings family +8-15%. Brass −3-5%. |
| **The Child at the Grate** | *"A child pressed its face to the grate. It wanted something. I said no."* | One random commodity spikes +12-20%. All others unaffected. |
| **The Man with the Case** | *"A man came with an empty case. He measured things. He wrote numbers. He left."* | Broad market volatility doubles for the next 6 hours. No directional bias. |
| **The Choir Director** | *"Someone was humming in the corridor. Four-part harmony. Imperfect intonation."* | Damp Sheet Music +10-18%. Reed Mold +5-10%. |
| **The Janitor** | *"The janitor came down to check the meters. He moved my crates. He rearranged the shelves."* | All prices reset 5-10% toward their 7-day moving average (mean reversion event). |
| **The Electrician** | *"Someone cut the power for eleven minutes. I sat in the dark and counted my teeth."* | Metronome Teeth +15-25%. Felt Hammers +8-12%. Everything else dips −2-4%. |
| **The Rat** | *"The large one was back. It took something. I will adjust the inventory."* | One random commodity drops −10-18%. |
| **Nobody** | *"Nobody came today. I am certain of this. And yet the shelves have moved."* | Small random walk applied to all commodities (±3-6%). Spooky flavor, minimal actual impact. |

**Frequency:** 1-3 visitor events per day, at semi-random intervals (minimum 4 hours apart). The specific visitor is chosen by weighted random selection — some are more common than others. "Nobody" is the most frequent; "The Man with the Case" is the rarest.

**Visitor Rotation:** Every month, one visitor is "retired" (stops appearing) and a new one is introduced. This keeps the system fresh and prevents complete mastery. Retired visitors can return later.

### 5.3 Layer Three: Resonance (Inter-Commodity Ripple Effects)

**Concept:** Musical instruments exhibit sympathetic resonance — strike a tuning fork and nearby strings tuned to the same frequency vibrate. The Exchange models this: when one commodity moves sharply, related commodities are pulled in the same or opposite direction after a short delay.

**Resonance Rules:**

1. **Same-family resonance (positive):** When a commodity moves more than ±8% in a 6-hour window, other commodities in the same instrument family are pulled in the **same direction** by 30-50% of the original move, applied over the next 2-4 hours.
   - Example: Brass Rot jumps +12% → Valve Oil is pulled up +4-6% over the next few hours.

2. **Cross-family resonance (negative):** When the Strings family moves sharply as a group (average move > ±6%), the Brass family tends to move in the **opposite direction** by 15-25% of the magnitude, and vice versa.
   - Example: Strings surge broadly → Brass dips slightly.

3. **Cascade threshold:** If three or more commodities move > ±10% in the same direction within a 4-hour window, a **cascade** is triggered — all remaining commodities are pulled ±5-8% in the same direction. This simulates a market-wide boom or crash. Cascades are rare (perhaps once every 1-2 weeks) but dramatic when they happen.

4. **Resonance dampening:** Each resonance effect decays with each hop. A resonance chain cannot propagate more than 2 levels deep (A affects B, B affects C, but C does not further propagate). This prevents infinite feedback loops.

**Resonance Map:**

```
Strings ←→ Strings (strong positive: 0.4)
Brass ←→ Brass (strong positive: 0.45)
Strings ←→ Brass (weak negative: -0.2)
Woodwind ←→ Strings (weak positive: 0.15)
Woodwind ←→ Brass (neutral: 0.05)
Percussion ←→ All (very weak positive: 0.08)
General ←→ All (very weak positive: 0.05)
```

**Drift:** Resonance strengths shift by ±0.05 every 10-14 days. A pair that was strongly correlated can weaken over time. Players must continuously re-evaluate their assumptions.

---

## 6. Price Calculation

Every **15 minutes**, the server recalculates prices for all 10 commodities using the following formula:

```
new_price = base_price
          × (1 + environmental_effect)
          × (1 + visitor_effect)
          × (1 + resonance_effect)
          × (1 + player_demand_effect)
          × (1 + random_noise)
          − storage_decay
```

Where:

- **base_price**: The commodity's long-term anchor price (slowly mean-reverts to prevent runaway inflation/deflation)
- **environmental_effect**: Dot product of the commodity's sensitivity vector and current Pipes values, scaled to ±5%
- **visitor_effect**: Active visitor impact, decaying over their influence window
- **resonance_effect**: Propagated effects from other commodity movements
- **player_demand_effect**: Net buy/sell pressure from player trades in the last 1-2 hours, scaled to ±3%
- **random_noise**: Gaussian noise, ±1-2% per tick (the irreducible chaos)
- **storage_decay**: See Section 7.3

**Price Bounds:** No commodity can fall below 10% of its anchor price or rise above 500%. If a price hits a bound, it triggers a "circuit breaker" — Enoch halts trading on that commodity for 1-2 hours, then reopens at a moderated price. This prevents total market collapse and adds a realistic mechanic.

---

## 7. Trading Mechanics

### 7.1 Buying and Selling

Enoch is the sole market maker. He always offers a **bid** (what he'll buy from you) and an **ask** (what he'll sell to you). The spread between them is his profit margin.

- **Spread:** 4-8% depending on the commodity's current volatility. Higher volatility = wider spread. This is realistic and discourages rapid-fire scalping.
- **Minimum trade:** 1 unit
- **Maximum trade per transaction:** 50 units (to prevent single trades from dominating the market)
- **Cooldown:** 30-second cooldown between trades on the same commodity (prevents bot-like behavior)

### 7.2 Portfolio

Each player has a portfolio showing:

- Current holdings (units of each commodity)
- Average purchase price per commodity (cost basis)
- Current market value per holding
- Unrealized profit/loss per holding
- Total portfolio value in Dust
- Available (unspent) Dust

### 7.3 Storage Fees

Enoch charges a daily **storage fee** for holding inventory in his sub-basement. This is deducted automatically at midnight (server time).

- **Fee:** 0.5% of the current market value of all holdings, per day
- **Minimum fee:** 1 Dust per day (if you hold anything at all)

Storage fees serve multiple purposes:
- Prevent infinite passive hoarding
- Create pressure to actively trade or sell
- Act as a Dust sink to control currency inflation
- Thematically, Enoch is charging rent for shelf space

If a player's Dust balance goes negative due to storage fees, Enoch forcibly liquidates their smallest holding to cover the debt. ("I sold your Rosin Dust. You were behind on rent. Do not look at me like that.")

### 7.4 Trade History

All trades are logged and visible to the player:
- Timestamp
- Commodity
- Buy/Sell
- Quantity
- Price per unit
- Total Dust exchanged
- Enoch's commentary on the trade (random quip)

---

## 8. Enoch's Role and Commentary

Enoch is not a passive shopkeeper. He has opinions about every transaction and every market movement. His commentary appears in a feed on the Exchange page and adds flavor to every interaction.

### 8.1 Trade Reactions

When a player buys:
- *"You want this? Fine. It is yours. Do not bring it back wet."*
- *"Interesting choice. The last person who bought Catgut in bulk was not seen again."*
- *"Money changes hands in the dark. I record everything."*

When a player sells:
- *"Returning it already? The shelf is still warm."*
- *"I will take it back. But I will remember that you gave up."*
- *"The price I offer is generous. I am feeling something adjacent to kindness."*

When a player makes a profit:
- *"You have done well. I do not say that often. I do not enjoy saying it now."*
- *"The numbers favor you today. Tomorrow the numbers may have different opinions."*

When a player takes a loss:
- *"The market giveth. The market taketh. I taketh a processing fee."*
- *"I tried to warn you. I did not actually try. But I thought about trying."*

### 8.2 Market Commentary (Feed)

A scrolling feed on the Exchange page shows Enoch's observations about market conditions, visitor events, and notable trades. This is the primary way players receive information about the hidden systems driving prices.

Examples:
- *"Brass Rot is climbing. I have seen this before. It never ends well for the brass."*
- *"There has been unusual interest in Felt Hammers. I do not know why. The moths are nervous."*
- *"The market is quiet. Too quiet. I have begun humming to fill the silence."*
- *"Three players sold Bow Hair in the last hour. The bundles pile up in the corner. They seem relieved."*

---

## 9. The Interface

### 9.1 Exchange Home

The main Exchange page, accessible from the site navigation. Layout:

- **Header:** "The Undercroft Exchange" — Enoch's avatar, player's Dust balance
- **Market Overview:** A grid of all 10 commodities showing current price, 24-hour change (%), and a tiny sparkline chart (7-day history)
- **Enoch's Feed:** A scrolling sidebar/strip of his commentary, visitor announcements, and environmental clues (most recent at top)
- **Quick Actions:** Tap any commodity to open its detail/trade view

### 9.2 Commodity Detail View

Tapping a commodity opens a detail panel:

- **Price chart:** Line chart showing price history (toggle between 24h, 7d, 30d views)
- **Current bid/ask:** Enoch's buy and sell prices with the spread shown
- **Buy/Sell controls:** Quantity input, total cost preview, confirm button
- **Your holdings:** Units held, cost basis, unrealized P&L
- **Recent trades:** Last 10 trades across all players on this commodity (anonymized: "A player bought 5 units at 12.4 Dust")

### 9.3 Portfolio View

A dedicated tab showing the player's full portfolio:

- Holdings breakdown with current values and P&L
- Total portfolio value over time (chart)
- Trade history log
- Daily storage fee tracker

### 9.4 Leaderboard: "The Ledger of Wealth"

A ranked list of players by total portfolio value (holdings + Dust). Updated in real time.

- Shows top 20 traders
- Highlights the current player's rank
- Optional: "All-time profit" leaderboard (cumulative realized gains)

### 9.5 Visual Theme

The Exchange should feel like a decrepit trading terminal rigged up in a damp basement:

- Dark background consistent with the Crypt's purple/gray palette
- Numbers displayed in a monospaced font, slightly flickering
- Price increases in sickly green, decreases in dull red
- Sparkline charts with no axes — just the shape of the price movement
- Enoch's feed styled like handwritten notes on damp paper
- Subtle ambient effects: occasional drip sound, faint hum of pipes

---

## 10. The Hidden Fourth Layer (Future Addition)

### "The Ledger Entries" — Match Activity Drives Supply

Once the base three layers are established and players are comfortable with the market, a secret fourth layer can be activated without announcement:

**Real chess activity on the site subtly influences commodity prices.**

- **More matches played in a day** → Enoch is busy maintaining boards → neglects inventory → broad supply drop → prices drift up
- **A match ends in checkmate** → Enoch rummages agitatedthrough shelves → one random commodity gets a small supply injection → price dips
- **A long match (40+ moves)** → Enoch was engrossed → market stalls briefly then jolts
- **Crypt activity** → Each wave cleared rattles the shelves → random commodity affected
- **Wager matches** → High-stakes environment → market volatility increases slightly for the next hour

This layer is never announced. The community discovers it organically. When someone posts "has anyone noticed Brass Rot dips every time there's a checkmate?" — that's the moment this layer pays off. It creates lore. It creates discovery. It makes the Exchange feel genuinely alive.

---

## 11. Anti-Abuse Considerations

- **Trade cooldowns** (30s per commodity) prevent automated scalping
- **Max trade size** (50 units) prevents market manipulation by single players
- **Storage fees** prevent infinite hoarding
- **Spread** ensures Enoch always takes a cut, making zero-skill rapid trading unprofitable
- **Circuit breakers** prevent extreme price exploitation
- **Sensitivity drift** prevents any permanent "solved" strategy
- **Daily Dust earning caps** are implicitly limited by match/activity frequency

---

## 12. Data Model (High-Level)

### Tables needed:

**`exchange_commodity`**
- `id`, `name`, `slug`, `description`, `instrument_family`
- `anchor_price` (long-term mean), `current_bid`, `current_ask`
- `sensitivity_temp`, `sensitivity_humidity`, `sensitivity_water`

**`exchange_price_history`**
- `id`, `commodity_id`, `price`, `timestamp`
- (One row per commodity per 15-minute tick — used for charts)

**`exchange_environment`**
- `id`, `temperature`, `humidity`, `water_level`, `timestamp`
- (One row per tick — the hidden Pipes state)

**`exchange_visitor_event`**
- `id`, `visitor_type`, `affected_commodities` (JSON), `magnitude`, `timestamp`, `enoch_text`

**`exchange_holding`**
- `id`, `user_id`, `commodity_id`, `quantity`, `avg_cost_basis`

**`exchange_trade`**
- `id`, `user_id`, `commodity_id`, `direction` (buy/sell), `quantity`, `price_per_unit`, `total_dust`, `timestamp`

**`exchange_portfolio_snapshot`**
- `id`, `user_id`, `total_value`, `dust_balance`, `timestamp`
- (Daily snapshot for portfolio chart)

**User model additions:**
- `dust_balance` (Integer, default 0)
- `exchange_unlocked` (Boolean — gated behind first login to Exchange page)

---

## 13. Rollout Plan

### Phase 1: Foundation
- Data models and price engine
- 10 commodities with base prices
- The Pipes (environmental cycle) running
- Basic buy/sell interface
- Portfolio view
- Enoch trade commentary
- Starting Dust grants

### Phase 2: Depth
- The Visitors (demand shocks) activated
- Resonance system activated
- Price charts (sparklines and detail views)
- Leaderboard
- Storage fees
- Enoch market commentary feed
- Trade history

### Phase 3: Polish
- Environmental clue system (Enoch's hints)
- Visitor lore and rotation
- Circuit breakers
- Sensitivity/resonance drift
- Sound effects and visual polish
- Mobile optimization

### Phase 4: The Secret Layer
- Ledger Entries (match activity influence) — activated silently
- Community discovers it on their own

---

## 14. Open Questions

1. **Should Dust ever convert to rating points?** If so, at what rate and with what limitations? This has major balance implications.
2. **Should players be able to trade Dust with each other directly?** This could create interesting social dynamics but also enables scams.
3. **Should there be "limited edition" commodities that appear for a week and then vanish?** This could drive speculative frenzies.
4. **Should the Exchange have "hours of operation" or be 24/7?** Closing it overnight could create opening-bell rush dynamics.
5. **Should the ElevenLabs voice be used for Enoch's market commentary?** Audio call-outs for major market events could be compelling.
6. **How should the Exchange interact with the weekly decree system?** Could a decree affect commodity prices? (e.g., "Extended Knight" week boosts Metronome Teeth because "the timing has changed.")

---

*Document prepared for the Chess Federation development roadmap. Not yet scheduled for implementation.*
