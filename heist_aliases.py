# -*- coding: utf-8 -*-
"""Map every name the wikis use for a heist onto our internal heist key.

Three relations matter and must not be conflated:
  same      -- two names for one heist ("Aftershock" == "Hoxton Revenge")
  variant   -- a DLC pack reusing another heist's map (Prison Nightmare runs the
               Hoxton Breakout map), so the achievements are genuinely shared
  other     -- a genuinely different heist
"""
import re

# wiki name -> internal key
ALIAS = {
    "aftershock": "aftershock",
    "hoxton’s revenge": "hoxton_revenge",
    "hoxton's revenge": "hoxton_revenge",
    "safehouse raid": "safe_house_raid",
    "safe house raid": "safe_house_raid",
    "the car shop": "car_shop",
    "car shop": "car_shop",
    "train heist": "transport_train",
    "transport: train heist": "transport_train",
    "transport: train": "transport_train",
    "santa’s workshop": "santa_workshop",
    "santa's workshop": "santa_workshop",
    "the white house": "white_house",
    "white house": "white_house",
    "the yacht heist": "yacht",
    "boat load": "yacht",          # holdout-map name of the Yacht
    "yacht heist": "yacht",
    "biker heist": "the_biker",
    "the biker heist": "the_biker",
    "the diamond": "the_diamond",
    "hell’s island": "hell_island",
    "hell's island": "hell_island",
    "henry’s rock": "henrys_rock",
    "henry's rock": "henrys_rock",
    "buluc's mansion": "bulucs_mansion",
    "safe house: nightmare": "safe_house_nightmare",
    "ukrainian prisoner": "ukrainian_prisoner",
    "the ukrainian prisoner": "ukrainian_prisoner",
    "go bank": "go_bank",
    "bank go": "go_bank",
    "alaskan deal": "alaskan_deal",
    "alesso": "the_alesso",
    "the alesso heist": "the_alesso",
    "cook off": "cook_off",
    "big bank": "big_bank",
    "the big bank": "big_bank",
    # registry pages whose name differs from the wiki's
    "reservoir dogs heist": "reservoir_dogs",
    "reservoir dogs": "reservoir_dogs",
    # The Diamond was merged into Diamond Heist (the DLC remastered that level)
    "the diamond heist": "diamond_heist",
    # folded multi-map parents
    "border crossing": "border_crossing_heists",
    "border crystals": "border_crossing_heists",
    "bomb: dockyard": "the_bomb_heists",
    "the bomb: dockyard": "the_bomb_heists",
    "the bomb: forest": "the_bomb_heists",
    "bomb: forest": "the_bomb_heists",
    "san martín bank": "san_martin",
    "san martin bank": "san_martin",
    "breakin' feds": "breakin_feds",
    "diamond heist": "diamond_heist",
    "diamond store": "diamond_store",
    "reservoir dogs": "reservoir_dogs",
    "boiling point": "boiling_point",
    "murky station": "murky_station",
    "murkywater station": "murky_station",
    "birth of sky": "birth_of_sky",
    "beneath the mountain": "beneath_mountain",
    "brooklyn 10-10": "brooklyn_1010",
    "brooklyn bank": "brooklyn_bank",
    "cursed kill room": "cursed_kill_room",
    "dragon heist": "dragon_heist",
    "hoxton breakout": "hoxton_breakout",
    "prison nightmare": "prison_nightmare",
    "lab rats": "lab_rats",
    "no mercy": "no_mercy",
    "panic room": "panic_room",
    "first world bank": "first_world_bank",
    "slaughterhouse": "slaughterhouse",
    "krasnirian slaughterhouse": "slaughterhouse",
    "framing frame": "framing_frame",
    "green bridge": "green_bridge",
    "heat street": "heat_street",
    "undercover": "undercover",
    "under the hammer": "under_the_hammer",
    "watchdogs": "watchdogs",
    "rats": "rats",
    "golden grin casino": "golden_grin",
    "hotline miami": "hotline_miami",
    "shadow raid": "shadow_raid",
    "stealing xmas": "stealing_xmas",
    "white xmas": "white_xmas",
    "meltdown": "meltdown",
    "mallcrasher": "mallcrasher",
    "nightclub": "nightclub",
    "art gallery": "art_gallery",
    "bank heist": "bank_heist",
    "big oil": "big_oil",
    "election day": "election_day",
    "firestarter": "firestarter",
    "four stores": "four_stores",
    "jewelry store": "jewelry_store",
    "goat simulator": "goat_simulator",
    "dragon heist": "dragon_heist",
    "scareface mansion": "scarface",
    "scarface mansion": "scarface",
    "scarface heist": "scarface",
    "shacklethorne auction": "shacklethorne",
    "breakfast in tijuana": "breakfast_tijuana",
    "breakin' feds": "breakin_feds",
    "san martín bank": "san_martin",
    "counterfeit": "counterfeit",
    "transport": "transport",
    "reservoir dogs": "reservoir_dogs",
    "ukrainian job": "ukrainian_job",
    "dragon heist": "dragon_heist",
    "murky station": "murky_station",
    "alaskan deal": "alaskan_deal",
}

# DLC packs that reuse another heist's map: their achievements legitimately show
# on both pages, but must be marked so they are not counted as new ones
VARIANT_PACK = {
    "hoxton_breakout": ["hoxton_breakout"],   # Prison Nightmare reuses this map
    "murky_station": ["murky_station"],
    "boiling_point": ["boiling_point"],
    "beneath_mountain": ["beneath_mountain"],
    "birth_of_sky": ["birth_of_sky"],
    "brooklyn_1010": ["brooklyn_1010"],
}


def norm(s):
    # "First World Bank (Payday 2)" and "First World Bank" are the same heist
    s = re.sub(r"\s*\(payday\s*2\)\s*$", "", (s or ""), flags=re.I)
    s = re.sub(r"[‘’]", "'", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def key_for(wiki_name):
    raw = re.sub(r"\s*\(payday\s*2\)\s*$", "", (wiki_name or "").strip(), flags=re.I)
    k = raw.lower()
    if k in ALIAS:
        return ALIAS[k]
    n = norm(wiki_name)
    for name, key in ALIAS.items():
        if norm(name) == n:
            return key
    return n.replace(" ", "_")