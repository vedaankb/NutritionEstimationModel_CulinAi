#!/bin/bash
# Quick training script for Layer 2

echo "🚀 Training Layer 2 Calibration Model..."
echo ""

# Check if dataset exists
if [ ! -f "data/processed/restaurant_nutrition_dataset.csv" ]; then
    echo "❌ Dataset not found!"
    echo "   Please run the notebook to generate the dataset first."
    echo "   Expected: data/processed/restaurant_nutrition_dataset.csv"
    exit 1
fi

# Run training
python3 layer2/train_model.py \
    --data data/processed/restaurant_nutrition_dataset.csv \
    --output layer2/trained_model.pkl \
    --max-samples 5000

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Training complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Test integration: python3 layer2/test_integration.py"
    echo "  2. Monitor confidence: python3 layer2/monitor_confidence.py"
else
    echo ""
    echo "❌ Training failed!"
    exit 1
fi
