"""The owner's 14 picked reels (3 Nov): saved to the queue as drafts in the
reel slots, drawn with the data-driven "board" visual. Run once from the
repo root; rendering happens in the workflow (`render` command)."""

import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import store  # noqa: E402

CTA = "Any doubts? Comment below or DM me on Instagram."
ASK = "\n\nAny doubts? Comment below or DM me on Instagram 👇"


def bars(unit, *items):
    return {"kind": "bars", "unit": unit,
            "items": [{"label": l, "value": v, "text": t, "color": c} for l, v, t, c in items]}


def check(*items):
    return {"kind": "check", "items": [{"text": t, "ok": ok} for t, ok in items]}


def steps(*items):
    return {"kind": "steps", "items": list(items)}


def number(value, label, sub="", color="teal"):
    return {"kind": "number", "value": value, "label": label, "sub": sub, "color": color}


def versus(lt, ll, lc, rt, rl, rc, win=None):
    return {"kind": "versus", "left": {"title": lt, "lines": ll, "color": lc},
            "right": {"title": rt, "lines": rl, "color": rc}, "win": win}


def gauge(value, text, label, color="green"):
    return {"kind": "gauge", "value": value, "text": text, "label": label, "color": color}


def s(heading, badge, viz):
    return {"heading": heading, "body": "", "badge": badge, "viz": viz}


REELS = [
    # ---- Fri 13 Nov ----
    dict(when="2026-11-13T18:00:00+05:30", music="upbeat", hook_type="warning",
         title="Service centre overcharging: what to question",
         hook="Don't say yes to these at your car service",
         youtube_title="Is the service centre overcharging you? 5 things to question",
         thumbnail_text="Service bill | too high?",
         slides=[s("Don't say yes to these at your car service", "", {}),
                 s("Ask for a written estimate first", "RULE 1",
                   steps("Written estimate before any work", "Approve every extra by phone",
                         "Ask to see the old parts")),
                 s("Common add-ons to question", "QUESTION THESE",
                   check(("Engine flush every service", False), ("Throttle or injector cleaning every time", False),
                         ("AC gas top-up without a leak check", False), ("Paid nitrogen top-ups", False))),
                 s("Check your owner's manual", "THE PROOF",
                   check(("Oil and filter: as per manual", True), ("Brake fluid: as per manual", True),
                         ("Parts due by km or months", True))),
                 s("Ask why. Then decide.", "MY RULE", number("ASK WHY", "before you pay", "Most add-ons are optional", "amber"))],
         voice_lines=[
             "Before any work starts, ask for a written estimate, and tell them to call you before adding anything extra. Ask to see the old parts too.",
             "Question these add-ons: an engine flush every service, throttle cleaning every time, an AC gas top-up without a leak check, and paid nitrogen.",
             "Your owner's manual says what's actually due, by kilometres or months. If it's not due, you can say no.",
             "Ask why, then decide. Most add-ons are optional. " + CTA],
         caption="My simple rule at every car service: ask why before you pay 🔧\n\n"
                 "1. Get a written estimate before any work starts.\n2. Tell them to call you before adding anything extra.\n"
                 "3. Ask to see the old parts.\n\nAdd-ons worth questioning: engine flush every service, throttle or injector "
                 "cleaning every time, AC gas top-up without a leak check, paid nitrogen top-ups.\n\n"
                 "Your owner's manual lists what's actually due by km or months. Not every add-on is a scam, but you should "
                 "know why you're paying for it. Save this for your next service." + ASK,
         hashtags=["#CarService", "#CarMaintenance", "#CarTips", "#IndianCars", "#CarOwners"],
         youtube_hashtags=["#CarService", "#CarTips"]),
    # ---- Sat 14 Nov ----
    dict(when="2026-11-14T18:00:00+05:30", music="tech", hook_type="mistake",
         title="Turbo petrol: don't switch off right after a hard drive",
         hook="Turbo petrol owners, don't switch off like this",
         youtube_title="Should you idle a turbo petrol before switching off?",
         thumbnail_text="Turbo car? | Don't do this",
         slides=[s("Turbo petrol owners, don't switch off like this", "", {}),
                 s("The turbo spins very fast and gets very hot", "WHY", number("VERY HOT", "turbo after a hard drive",
                                                                                 "Oil cools its bearings", "red")),
                 s("After a fast highway run, idle first", "THE FIX",
                   steps("Fast highway run or steep climb", "Idle 30 to 60 seconds", "Then switch off")),
                 s("Normal city driving? No need", "GOOD NEWS",
                   check(("Gentle city drive: switch off normally", True), ("Revving before switch off", False),
                         ("Hard driving on a cold engine", False))),
                 s("Gentle first, gentle last", "MY RULE", number("30-60 s", "idle after a hard drive",
                                                                   "VW and Skoda TSI owners, this one's for you", "teal"))],
         voice_lines=[
             "Your turbo spins very fast and gets very hot. Engine oil cools its bearings, but only while the engine runs.",
             "So after a fast highway run or a steep climb, let it idle for thirty to sixty seconds, then switch off.",
             "In normal city driving there's no need. And never rev the engine just before switching off, or drive hard while it's cold.",
             "Gentle for the first few kilometres, gentle for the last. " + CTA],
         caption="If you drive a turbo petrol (VW and Skoda TSI owners, this is you), this small habit protects the turbo 🔥\n\n"
                 "After a fast highway run or a steep ghat climb, let the engine idle for 30 to 60 seconds before switching "
                 "off. The oil keeps cooling the turbo's bearings while the engine runs.\n\nNormal city driving? Just switch "
                 "off as usual. Modern turbos are water-cooled too, so this is only about hard drives.\n\nAvoid: revving "
                 "before switching off, and driving hard while the engine is still cold." + ASK,
         hashtags=["#TurboPetrol", "#VolkswagenIndia", "#SkodaIndia", "#TSI", "#CarTips"],
         youtube_hashtags=["#Volkswagen", "#Skoda"]),
    # ---- Sun 15 Nov ----
    dict(when="2026-11-15T18:00:00+05:30", music="upbeat", hook_type="number",
         title="5 checks before a long road trip",
         hook="Do these 5 checks before your next road trip",
         youtube_title="What to check before a long road trip in India",
         thumbnail_text="Road trip? | 5 checks",
         slides=[s("Do these 5 checks before your next road trip", "", {}),
                 s("Tyres first, spare included", "CHECK 1-2",
                   check(("Tyre pressure, cold, as per door sticker", True), ("Spare tyre pressure", True),
                         ("Cuts or bulges on the sidewall", True))),
                 s("Fluids, with the engine cold", "CHECK 3",
                   check(("Engine oil between min and max", True), ("Coolant at the mark", True),
                         ("Washer fluid full", True))),
                 s("See and be seen", "CHECK 4",
                   check(("Wipers clear the glass", True), ("All lights and indicators work", True))),
                 s("Brakes feel right", "CHECK 5",
                   check(("Pedal firm, no squeal", True), ("No pull to one side", True)))],
         voice_lines=[
             "First, tyres. Check the pressure cold, as per the door sticker, the spare too, and look for cuts or bulges.",
             "Next, fluids with the engine cold: engine oil between min and max, coolant at the mark, and washer fluid full.",
             "Then make sure the wipers clear the glass, and every light and indicator works.",
             "Last, the brakes should feel firm, with no squeal and no pull. Safe trip! " + CTA],
         caption="Wedding season road trips are here 🚗 Five quick checks before you leave, all doable in your parking:\n\n"
                 "1. Tyre pressure (cold), as per the door sticker\n2. Spare tyre pressure, and no cuts or bulges\n"
                 "3. Engine oil, coolant and washer fluid, with the engine cold\n4. Wipers and all lights\n"
                 "5. Brakes: firm pedal, no squeal, no pull\n\nSave this and run through it before your next trip." + ASK,
         hashtags=["#RoadTrip", "#CarMaintenance", "#CarTips", "#IndianRoads", "#CarCare"],
         youtube_hashtags=["#RoadTrip", "#CarTips"]),
    # ---- Tue 17 Nov (YouTube) ----
    dict(when="2026-11-17T19:30:00+05:30", music="chill", hook_type="myth",
         title="Does CNG damage the engine?",
         hook="Does CNG damage your engine?",
         youtube_title="Does CNG damage the car engine? Myth vs fact",
         thumbnail_text="Does CNG | damage engines?",
         slides=[s("Does CNG damage your engine?", "", {}),
                 s("Factory-fitted CNG is built for it", "MYTH VS FACT",
                   versus("Factory kit", ["Engine tuned for CNG", "Covered by warranty"], "green",
                          "Cheap aftermarket kit", ["Poor tuning", "Can run hot"], "red", "left")),
                 s("What you give up", "THE TRADE-OFF",
                   check(("Some power, felt on climbs", False), ("Boot space for the cylinder", False),
                         ("Much lower running cost", True))),
                 s("Keep it healthy", "CARE TIPS",
                   steps("Keep some petrol in the tank", "Spark plugs checked more often",
                         "Cylinder test every 3 years")),
                 s("Use a factory or approved kit", "MY RULE",
                   number("NO", "damage with proper care", "Factory or approved kit, regular service", "green"))],
         voice_lines=[
             "A factory-fitted CNG car has an engine tuned for it, and it's covered by warranty. Badly fitted cheap kits are where problems start.",
             "What you give up is some power, which you'll feel on climbs, and boot space for the cylinder. What you gain is a much lower running cost.",
             "Keep some petrol in the tank, get the spark plugs checked more often, and get the cylinder tested every three years.",
             "So no, CNG doesn't damage a properly fitted, well serviced engine. " + CTA],
         caption="Does CNG damage the engine? Short answer: not when it's factory-fitted or an approved kit, and serviced on time ⛽\n\n"
                 "✅ Factory CNG: engine tuned for it, warranty covered\n❌ Cheap, badly tuned aftermarket kits: that's where "
                 "trouble starts\n\nTrade-offs: a little less power on climbs and less boot space, for a much lower running cost.\n\n"
                 "Care tips: keep some petrol in the tank, check spark plugs more often, and get the cylinder tested every 3 years." + ASK,
         hashtags=["#CNG", "#CNGCars", "#CarMyths", "#IndianCars", "#CarTips"],
         youtube_hashtags=["#CNG", "#CarMyths"]),
    # ---- Wed 18 Nov (YouTube) ----
    dict(when="2026-11-18T19:30:00+05:30", music="epic", hook_type="question",
         title="Bharat NCAP 5 stars: what it really means",
         hook="5 stars doesn't mean what you think",
         youtube_title="Bharat NCAP 5 star rating explained: what it really means",
         thumbnail_text="5 star safety? | Read this",
         slides=[s("5 stars doesn't mean what you think", "", {}),
                 s("There are two ratings, not one", "TWO SCORES",
                   versus("Adult", ["Out of 32 points", "Front and side crash"], "teal",
                          "Child", ["Out of 49 points", "Child seats tested"], "amber")),
                 s("Tested at 64 km/h", "THE TEST",
                   number("64 km/h", "frontal offset crash", "Not a highway-speed crash", "amber")),
                 s("The rating is for the variant tested", "CHECK THIS",
                   check(("Which variant was tested", True), ("Airbags and ESC in your variant", True),
                         ("Adult AND child scores", True))),
                 s("Stars help. Seat belts save.", "MY RULE",
                   number("BELT UP", "front and rear", "Rear seat belts too", "green"))],
         voice_lines=[
             "Bharat NCAP gives two ratings: adult protection, out of thirty two points, and child protection, out of forty nine. Check both.",
             "The main frontal crash is at sixty four kilometres per hour. That's not a highway speed crash, so drive accordingly.",
             "And the rating is for the variant they tested. Check that your variant has the same airbags and E S C.",
             "Stars help, but seat belts save lives, in the rear seat too. " + CTA],
         caption="A 5-star Bharat NCAP rating is great, but read it properly ⭐\n\n"
                 "• Two ratings: Adult Occupant (out of 32) and Child Occupant (out of 49). Check both.\n"
                 "• The frontal offset test is at 64 km/h, not highway speed.\n"
                 "• The rating applies to the variant tested. Make sure yours has the same airbags and ESC.\n\n"
                 "Stars help, seat belts save. Rear passengers too." + ASK,
         hashtags=["#BharatNCAP", "#CarSafety", "#5StarSafety", "#IndianCars", "#CarTips"],
         youtube_hashtags=["#BharatNCAP", "#CarSafety"]),
    # ---- Fri 20 Nov ----
    dict(when="2026-11-20T18:00:00+05:30", music="tech", hook_type="question",
         title="E20 petrol: what it does to your car",
         hook="E20 petrol in your tank: what changes?",
         youtube_title="Is E20 petrol bad for my car? Mileage and engine explained",
         thumbnail_text="E20 petrol | bad for cars?",
         slides=[s("E20 petrol in your tank: what changes?", "", {}),
                 s("20% ethanol, 80% petrol", "WHAT IT IS",
                   bars("share of the fuel", ("Petrol", 80, "80%", "amber"), ("Ethanol", 20, "20%", "green"))),
                 s("Check your fuel lid", "IS YOUR CAR READY?",
                   check(("E20 sticker on the fuel lid: made for it", True), ("Most cars from April 2023 on", True),
                         ("Older car: ask your service centre", True))),
                 s("Mileage drops a little", "MILEAGE",
                   bars("approx. mileage drop", ("E20-ready car", 2, "about 1-2%", "green"),
                        ("Older car", 6, "a few %", "amber"))),
                 s("Older car? Check rubber parts at service", "MY RULE",
                   number("E20", "check the fuel lid", "Older cars: rubber parts at service", "teal"))],
         voice_lines=[
             "E20 is twenty percent ethanol and eighty percent petrol. It's what most pumps in India sell now.",
             "Check your fuel lid. An E20 sticker means your car is made for it. Most cars made from April 2023 are.",
             "Mileage drops a little: about one to two percent in E20 ready cars, and a few percent in older ones.",
             "Older car? Ask your service centre to check rubber parts like fuel hoses at the next service. " + CTA],
         caption="E20 petrol: what it means for your car ⛽\n\n• E20 = 20% ethanol + 80% petrol\n"
                 "• Look for the E20 sticker on your fuel lid. Most cars made from April 2023 are E20-ready.\n"
                 "• Mileage: roughly 1-2% lower in E20-ready cars, a few % in older cars (approximate, varies by car)\n"
                 "• Older car? Ask the service centre to check rubber parts like fuel hoses and seals at the next service.\n\n"
                 "Noticed a mileage change since E20? Tell me 👇" + ASK,
         hashtags=["#E20Petrol", "#Ethanol", "#Mileage", "#IndianCars", "#CarTips"],
         youtube_hashtags=["#E20", "#Mileage"]),
    # ---- Sat 21 Nov ----
    dict(when="2026-11-21T18:00:00+05:30", music="chill", hook_type="warning",
         title="Car battery dies when parked for days",
         hook="Parking your car for a week? Do this first",
         youtube_title="Why does my car battery die when parked? How to prevent it",
         thumbnail_text="Dead battery | after parking?",
         slides=[s("Parking your car for a week? Do this first", "", {}),
                 s("A parked car still uses power", "WHY",
                   gauge(0.35, "LOW", "battery after weeks parked", "red")),
                 s("Drive it once a week", "THE FIX",
                   check(("Drive 20 to 30 minutes weekly", True), ("Idling for 2 minutes", False),
                         ("Lights or dashcam left on", False))),
                 s("Away for weeks?", "LONG BREAK",
                   steps("Ask someone to drive it weekly", "Or use a battery maintainer",
                         "Or disconnect the negative terminal")),
                 s("Slow start is the first warning", "WARNING SIGNS",
                   check(("Slow, weak cranking", False), ("White crust on terminals", False),
                         ("Battery over 3 to 4 years old", False)))],
         voice_lines=[
             "Even when parked, your car's computers and alarm draw a little power, so a battery can go flat in a few weeks.",
             "Drive it for twenty to thirty minutes once a week. Just idling for two minutes doesn't recharge it.",
             "Away for longer? Ask someone to drive it, use a battery maintainer, or disconnect the negative terminal.",
             "Warning signs: slow cranking, white crust on the terminals, and a battery over three or four years old. " + CTA],
         caption="Car parked for a week or more? Your battery is still working 🔋\n\nThe alarm and computers draw a little power "
                 "all the time, so a battery can go flat in a few weeks.\n\n✅ Drive 20-30 minutes once a week\n"
                 "❌ Idling for 2 minutes doesn't recharge it\n\nAway longer: someone drives it weekly, a battery maintainer, "
                 "or disconnect the negative terminal (some settings may reset).\n\nWarning signs: slow cranking, white crust "
                 "on terminals, battery older than 3-4 years in Indian heat." + ASK,
         hashtags=["#CarBattery", "#CarMaintenance", "#CarTips", "#IndianCars", "#CarCare"],
         youtube_hashtags=["#CarBattery", "#CarTips"]),
    # ---- Sun 22 Nov ----
    dict(when="2026-11-22T18:00:00+05:30", music="upbeat", hook_type="versus",
         title="Buy a car in December or January?",
         hook="Buying a car? December or January?",
         youtube_title="Should I buy a car in December or January? Year end discount explained",
         thumbnail_text="December or | January?",
         slides=[s("Buying a car? December or January?", "", {}),
                 s("December: bigger discounts", "DECEMBER",
                   versus("December", ["Bigger discounts", "Year-end offers"], "green",
                          "January", ["Price hikes likely", "Newer year on paper"], "amber")),
                 s("But the year counts at resale", "THE CATCH",
                   number("1 YEAR", "older on paper", "A December car looks a year older within weeks", "amber")),
                 s("Check the manufacturing date", "CHECK THIS",
                   check(("Manufacturing month on the VIN plate", True), ("Avoid stock many months old", True),
                         ("Get the discount in writing", True))),
                 s("Keeping it long? December wins", "MY RULE",
                   versus("Keep 7+ years", ["Take the December deal"], "green",
                          "Sell in 2-3 years", ["Think about January"], "amber"))],
         voice_lines=[
             "December has the biggest year end discounts. From January, prices often go up.",
             "The catch: a car bought in December looks a year older on paper within weeks, which matters at resale.",
             "Whenever you buy, check the manufacturing month on the VIN plate, avoid very old stock, and get the discount in writing.",
             "Keeping it seven years or more? Take the December deal. Selling in two or three? Think about January. " + CTA],
         caption="December or January, when should you buy your car? 🗓️\n\nDecember: the biggest year-end discounts. "
                 "January: prices often go up.\n\nThe catch: a December car is a year older on paper within weeks, which "
                 "shows at resale.\n\nWhenever you buy:\n• Check the manufacturing month on the VIN plate\n"
                 "• Avoid stock that's many months old\n• Get the discount in writing\n\n"
                 "Keeping it 7+ years? Take the December deal. Selling in 2-3? January may suit you." + ASK,
         hashtags=["#CarBuying", "#YearEndOffers", "#NewCar", "#IndianCars", "#CarTips"],
         youtube_hashtags=["#CarBuying", "#NewCar"]),
    # ---- Tue 24 Nov (YouTube) ----
    dict(when="2026-11-24T19:30:00+05:30", music="tech", hook_type="question",
         title="Can you own an EV without home charging?",
         hook="No home charger? Watch this before buying an EV",
         youtube_title="Can I own an electric car without home charging in India?",
         thumbnail_text="EV without | home charger?",
         slides=[s("No home charger? Watch this before buying an EV", "", {}),
                 s("Public fast charging costs much more", "THE COST",
                   bars("approx. per unit", ("Home", 8, "about Rs 8", "green"), ("Public DC", 22, "Rs 20+", "red"))),
                 s("It can still work if...", "WHEN IT WORKS",
                   check(("Charging at office or society", True), ("A charger near home you use weekly", True),
                         ("Mostly long highway runs", False))),
                 s("Count the time too", "TIME",
                   number("WEEKLY", "a charging stop", "Plan it like a fuel stop", "amber")),
                 s("No regular charging spot? Pick hybrid or CNG", "MY RULE",
                   versus("Regular spot", ["EV makes sense"], "green", "No spot", ["Hybrid or CNG"], "amber"))],
         voice_lines=[
             "At home, a unit costs about eight rupees. Public fast chargers often charge over twenty, so your cost per kilometre can nearly triple.",
             "It can still work if you can charge at your office or society, or there's a charger near home you'll actually use every week.",
             "Count the time too. A weekly charging stop is like a fuel stop, just longer.",
             "No regular charging spot? A hybrid or CNG car will be easier. " + CTA],
         caption="Thinking EV but no charger at home? ⚡\n\nHome charging: roughly ₹8 a unit. Public DC fast charging: often "
                 "₹20+ a unit. Your cost per km can nearly triple (approximate, varies by city and charger).\n\n"
                 "It can still work if:\n✅ You can charge at your office or society\n✅ There's a charger near home you'll "
                 "use weekly\n\nNo regular charging spot? A hybrid or CNG car is the easier life." + ASK,
         hashtags=["#EVIndia", "#ElectricCars", "#EVCharging", "#EVTips", "#CarTech"],
         youtube_hashtags=["#EVIndia", "#EVCharging"]),
    # ---- Wed 25 Nov (YouTube) ----
    dict(when="2026-11-25T19:30:00+05:30", music="chill", hook_type="number",
         title="How much range does the AC eat in an EV?",
         hook="How much range does AC eat in an EV?",
         youtube_title="How much range does AC use in an electric car?",
         thumbnail_text="EV range | AC on?",
         slides=[s("How much range does AC eat in an EV?", "", {}),
                 s("Usually 10 to 20% in Indian heat", "THE NUMBER",
                   bars("range left (example)", ("AC off", 100, "100%", "green"), ("AC on", 85, "about 85%", "amber"))),
                 s("City traffic feels it most", "WHY",
                   number("CITY", "AC runs, car crawls", "More of your battery goes to cooling", "amber")),
                 s("Get it back", "TIPS",
                   check(("Pre-cool while plugged in", True), ("Recirculation once cool", True),
                         ("Park in shade", True))),
                 s("Use the AC. Just use it smart.", "MY RULE",
                   number("SMART AC", "comfort and range", "Eco mode helps too", "teal"))],
         voice_lines=[
             "In Indian heat, the AC usually takes about ten to twenty percent of an EV's range.",
             "City traffic feels it most, because the AC keeps running while the car barely moves.",
             "Pre-cool the cabin while it's plugged in, switch to recirculation once it's cool, and park in shade.",
             "So use the AC, just use it smartly. " + CTA],
         caption="How much range does the AC take in an EV? ❄️\n\nUsually about 10-20% in Indian heat (approximate, depends on "
                 "car, temperature and traffic). City crawling feels it most.\n\nGet some back:\n• Pre-cool while plugged in\n"
                 "• Recirculation once the cabin is cool\n• Park in shade\n• Eco AC mode if your car has it" + ASK,
         hashtags=["#EVIndia", "#EVRange", "#ElectricCars", "#EVTips", "#CarTech"],
         youtube_hashtags=["#EVIndia", "#EVRange"]),
    # ---- Fri 27 Nov ----
    dict(when="2026-11-27T18:00:00+05:30", music="epic", hook_type="versus",
         title="Petrol vs diesel vs CNG vs EV: cost per km",
         hook="Petrol, diesel, CNG or EV: which costs least per km?",
         youtube_title="Petrol vs diesel vs CNG vs EV: running cost per km in India",
         thumbnail_text="Cheapest | per km?",
         slides=[s("Petrol, diesel, CNG or EV: which costs least per km?", "", {}),
                 s("Running cost per km", "THE NUMBERS",
                   bars("example Rs per km", ("Petrol", 6.4, "about Rs 6.4", "red"), ("Diesel", 4.5, "about Rs 4.5", "amber"),
                        ("CNG", 3.3, "about Rs 3.3", "teal"), ("EV (home)", 1.2, "about Rs 1.2", "green"))),
                 s("But the car costs more upfront", "THE CATCH",
                   check(("Diesel, CNG and EV cost more to buy", False), ("Savings need kilometres", True))),
                 s("Match it to your monthly km", "PICK BY KM",
                   steps("Under 1,000 km a month: petrol is fine", "1,000 to 2,000: CNG or hybrid",
                         "Lots of km and home charging: EV")),
                 s("Do the maths for your km", "MY RULE",
                   number("YOUR KM", "decides the fuel", "Use your city's prices", "teal"))],
         voice_lines=[
             "With example prices, petrol costs about six rupees forty a kilometre, diesel about four fifty, CNG about three thirty, and an EV charged at home about one twenty.",
             "But diesel, CNG and EVs cost more to buy, so the savings only come with kilometres.",
             "Under a thousand kilometres a month, petrol is fine. One to two thousand, look at CNG or a hybrid. Lots of kilometres and home charging, an EV.",
             "Do the maths with your own kilometres and your city's prices. " + CTA],
         caption="Which fuel costs least per km? ⛽⚡\n\nExample numbers (your city's prices will differ):\n"
                 "• Petrol: about ₹6.4/km (₹103/l at 16 km/l)\n• Diesel: about ₹4.5/km (₹90/l at 20 km/l)\n"
                 "• CNG: about ₹3.3/km (₹85/kg at 26 km/kg)\n• EV at home: about ₹1.2/km (₹8/unit at 7 km/unit)\n\n"
                 "But diesel, CNG and EVs cost more to buy, so the savings need kilometres.\n\n"
                 "Under 1,000 km/month: petrol is fine. 1,000-2,000: CNG or hybrid. Lots of km + home charging: EV.\n\n"
                 "What's your monthly km? Tell me and I'll tell you what I'd pick 👇" + ASK,
         hashtags=["#PetrolVsDiesel", "#CNG", "#EVIndia", "#RunningCost", "#IndianCars"],
         youtube_hashtags=["#CNG", "#EVIndia"]),
    # ---- Sat 28 Nov ----
    dict(when="2026-11-28T18:00:00+05:30", music="tech", hook_type="versus",
         title="AMT vs CVT vs DCT vs torque converter",
         hook="AMT, CVT, DCT or torque converter: which automatic?",
         youtube_title="AMT vs CVT vs DCT vs torque converter: which automatic is best in India?",
         thumbnail_text="Which automatic | is best?",
         slides=[s("AMT, CVT, DCT or torque converter: which automatic?", "", {}),
                 s("AMT vs CVT", "ROUND 1",
                   versus("AMT", ["Cheapest", "Jerky shifts", "Good mileage"], "amber",
                          "CVT", ["Very smooth", "Great in city", "Rubber-band feel"], "teal")),
                 s("DCT vs torque converter", "ROUND 2",
                   versus("DCT", ["Fastest shifts", "Efficient", "Hates slow crawling"], "blue",
                          "Torque converter", ["Smooth", "Tough", "Slightly thirstier"], "green")),
                 s("Which one for you?", "PICK",
                   steps("Tight budget: AMT", "City comfort: CVT or torque converter",
                         "Highway fun: DCT, drive it smoothly in traffic")),
                 s("Test drive it in traffic", "MY RULE",
                   number("TRAFFIC", "test drive it there", "Not just on an empty road", "teal"))],
         voice_lines=[
             "An AMT is the cheapest and gives good mileage, but shifts can feel jerky. A CVT is very smooth in the city, with a rubber band feel when you push it.",
             "A DCT shifts fastest and is efficient, but doesn't like slow crawling. A torque converter is smooth and tough, and slightly thirstier.",
             "Tight budget, AMT. City comfort, CVT or torque converter. Highway fun, DCT, driven smoothly in traffic.",
             "Whichever you pick, test drive it in real traffic. " + CTA],
         caption="Which automatic should you buy? 🚗\n\n• AMT: cheapest, good mileage, shifts can feel jerky\n"
                 "• CVT: very smooth in the city, rubber-band feel when pushed\n• DCT: fastest shifts, efficient, doesn't "
                 "like slow crawling (be smooth in traffic)\n• Torque converter: smooth and tough, slightly thirstier\n\n"
                 "Tight budget: AMT. City comfort: CVT or torque converter. Highway fun: DCT.\n\nWhichever you pick, test "
                 "drive it in real traffic. Which one do you drive? 👇" + ASK,
         hashtags=["#AutomaticCars", "#DCT", "#CVT", "#IndianCars", "#CarTech"],
         youtube_hashtags=["#AutomaticCars", "#DCT"]),
    # ---- Sun 29 Nov ----
    dict(when="2026-11-29T18:00:00+05:30", music="upbeat", hook_type="warning",
         title="Read the tyre DOT date before buying",
         hook="Read this 4-digit code before you buy tyres",
         youtube_title="How to check tyre manufacturing date (DOT code) before buying",
         thumbnail_text="Check this | tyre code",
         slides=[s("Read this 4-digit code before you buy tyres", "", {}),
                 s("Week, then year", "HOW TO READ IT",
                   versus("Week", ["First 2 digits", "e.g. 23"], "teal", "Year", ["Last 2 digits", "e.g. 25 = 2025"], "amber")),
                 s("2325 = 23rd week of 2025", "EXAMPLE",
                   number("2325", "week 23 of 2025", "Find it on the sidewall", "teal")),
                 s("Buying new tyres?", "WHEN BUYING",
                   check(("Made within the last year", True), ("Several years old in the shop", False))),
                 s("Rubber ages even unused", "MY RULE",
                   check(("Replace at the tread wear bars", True), ("Old tyres with cracks: replace", True)))],
         voice_lines=[
             "Look for a four digit code on the tyre's sidewall. The first two digits are the week, the last two are the year.",
             "So two three two five means the twenty third week of twenty twenty five.",
             "When buying new tyres, ask for ones made within the last year, not stock that's been sitting for years.",
             "Rubber ages even when unused. Replace at the tread wear bars, or sooner if you see cracks. " + CTA],
         caption="Before you buy tyres, read this 4-digit code on the sidewall 🛞\n\n"
                 "First 2 digits = week, last 2 = year. Example: 2325 = 23rd week of 2025.\n\n"
                 "✅ Buy tyres made within the last year\n❌ Avoid stock that's been sitting for years\n\n"
                 "Rubber ages even unused. Replace at the tread wear bars, or sooner if you see cracks." + ASK,
         hashtags=["#Tyres", "#TyreCare", "#CarTips", "#IndianCars", "#CarMaintenance"],
         youtube_hashtags=["#Tyres", "#CarTips"]),
    # ---- Tue 1 Dec (YouTube) ----
    dict(when="2026-12-01T19:30:00+05:30", music="chill", hook_type="question",
         title="How long does an EV battery last in India?",
         hook="How long does an EV battery really last?",
         youtube_title="How long does an EV battery last in India? Warranty and replacement",
         thumbnail_text="EV battery | life?",
         slides=[s("How long does an EV battery really last?", "", {}),
                 s("Most come with a long warranty", "WARRANTY",
                   number("8 YEARS", "common battery warranty", "Often 1.6 lakh km, check your brand", "teal")),
                 s("It fades slowly, it doesn't just die", "HEALTH",
                   gauge(0.8, "~80%", "health after many years", "green")),
                 s("What wears it faster", "AVOID",
                   check(("Charging to 100% every day", False), ("Only DC fast charging", False),
                         ("Parking in hot sun", False))),
                 s("Daily 20 to 80%, full only for trips", "MY RULE",
                   number("20-80%", "daily charge range", "Full charge before long trips is fine", "green"))],
         voice_lines=[
             "Most EVs in India come with a battery warranty of around eight years, often with a kilometre limit. Check your brand.",
             "The battery fades slowly over the years. It doesn't just die one day.",
             "What wears it faster: charging to a hundred percent every day, only using fast chargers, and parking in hot sun.",
             "Keep daily charging between twenty and eighty percent, and charge full only before trips. " + CTA],
         caption="How long does an EV battery last? 🔋\n\n• Most EVs in India come with a battery warranty of around 8 years, "
                 "often with a km limit (check your brand's exact terms)\n• Batteries fade slowly; they don't suddenly die\n\n"
                 "Wears it faster: 100% every day, only DC fast charging, parking in hot sun.\n\n"
                 "My rule: 20-80% daily, full charge only before long trips." + ASK,
         hashtags=["#EVIndia", "#EVBattery", "#ElectricCars", "#EVTips", "#CarTech"],
         youtube_hashtags=["#EVIndia", "#EVBattery"]),
]


def main():
    made = []
    for r in REELS:
        post_id = format(zlib.crc32(r["title"].encode()), "08x")
        when = r.pop("when")
        day = __import__("datetime").datetime.fromisoformat(when).strftime("%a")
        post = {"format": "reel", "reel_style": "board", "layout": "captions", "status": "draft",
                "id": post_id, "scheduled_for": when, "save_tip": r["slides"][-1]["heading"],
                **r}
        if day not in ("Fri", "Sat", "Sun"):
            post["youtube_only"] = True
        store.save_post(post)
        made.append(post_id)
        print(post_id, when[:16], post["title"])
    json.dump(made, open("scripts/new_reels_nov.ids.json", "w"))


if __name__ == "__main__":
    main()
