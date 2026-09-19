def get_food_suggestions(text):

    text = text.lower()

    foods = []

    # Protein
    if "protein" in text or "chicken" in text:
        foods.append("Boiled chicken")

    # Vegetables
    if "vegetable" in text or "vegetables" in text:
        foods.append("Dog-safe cooked vegetables")

    # Rice
    if "rice" in text:
        foods.append("Plain cooked rice")

    # Pumpkin
    if "pumpkin" in text:
        foods.append("Plain cooked pumpkin")

    # Egg
    if "egg" in text:
        foods.append("Boiled egg")

    # General suggestion if nothing is detected
    if len(foods) == 0:
        foods = [
            "Use food recommended by your veterinarian",
            "Provide fresh drinking water"
        ]

    return foods