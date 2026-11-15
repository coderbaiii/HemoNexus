"""
Machine Learning Training Pipeline for HemoNexus Donor Return & Response Prediction
Trained on the Real-World UCI Blood Transfusion Service Center Dataset (748 donor records).
Feature inputs:
  1. Recency (months since last donation)
  2. Frequency (total number of donations)
  3. Monetary (total volume in c.c.)
  4. Time (months since first donation)
Target:
  Donor returned/donated in target window (0 or 1).
"""

import os
import csv
import math
import json
import random

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uci_blood_transfusion.csv")
MODEL_OUT = os.path.join(os.path.dirname(__file__), "trained_donor_weights.json")

def sigmoid(z):
    z = max(-500.0, min(500.0, z))
    return 1.0 / (1.0 + math.exp(-z))

def load_data():
    X = []
    y = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row or len(row) < 5:
                continue
            r = float(row[0].strip())
            freq = float(row[1].strip())
            mon = float(row[2].strip())
            t = float(row[3].strip())
            label = int(row[4].strip())
            X.append([r, freq, mon, t])
            y.append(label)
    return X, y

def normalize_features(X):
    n_features = len(X[0])
    means = [0.0] * n_features
    stds = [0.0] * n_features
    n = len(X)
    
    for row in X:
        for j in range(n_features):
            means[j] += row[j]
    means = [m / n for m in means]
    
    for row in X:
        for j in range(n_features):
            stds[j] += (row[j] - means[j]) ** 2
    stds = [math.sqrt(s / (n - 1)) if s > 0 else 1.0 for s in stds]
    
    X_norm = []
    for row in X:
        norm_row = [(row[j] - means[j]) / stds[j] for j in range(n_features)]
        X_norm.append(norm_row)
        
    return X_norm, means, stds

def train_logistic_regression(X_train, y_train, epochs=1500, lr=0.05, reg=0.01):
    n_samples = len(X_train)
    n_features = len(X_train[0])
    
    # Initialize weights and bias
    weights = [0.0] * n_features
    bias = 0.0
    
    for epoch in range(epochs):
        dw = [0.0] * n_features
        db = 0.0
        total_loss = 0.0
        
        for i in range(n_samples):
            z = sum(weights[j] * X_train[i][j] for j in range(n_features)) + bias
            p = sigmoid(z)
            error = p - y_train[i]
            
            for j in range(n_features):
                dw[j] += error * X_train[i][j]
            db += error
            
            # Binary Cross Entropy Loss
            p_safe = max(1e-15, min(1.0 - 1e-15, p))
            total_loss += -(y_train[i] * math.log(p_safe) + (1.0 - y_train[i]) * math.log(1.0 - p_safe))
            
        # Gradient update with L2 regularization
        for j in range(n_features):
            weights[j] -= lr * (dw[j] / n_samples + reg * weights[j])
        bias -= lr * (db / n_samples)
        
    return weights, bias

def evaluate(X_test, y_test, weights, bias):
    n = len(X_test)
    correct = 0
    tp = fp = tn = fn = 0
    
    for i in range(n):
        z = sum(weights[j] * X_test[i][j] for j in range(n_features)) + bias
        prob = sigmoid(z)
        pred = 1 if prob >= 0.5 else 0
        
        if pred == y_test[i]:
            correct += 1
        if pred == 1 and y_test[i] == 1:
            tp += 1
        elif pred == 1 and y_test[i] == 0:
            fp += 1
        elif pred == 0 and y_test[i] == 0:
            tn += 1
        elif pred == 0 and y_test[i] == 1:
            fn += 1
            
    accuracy = correct / n
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1 * 100, 2),
        "total_samples": n
    }

if __name__ == "__main__":
    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    print("Loading real-world blood transfusion dataset...")
    X, y = load_data()
    print(f"Loaded {len(X)} donor records.")
    
    X_norm, means, stds = normalize_features(X)
    n_features = len(X_norm[0])
    
    # Stratified 80/20 train/test split
    combined = list(zip(X_norm, y))
    random.seed(42)
    random.shuffle(combined)
    split_idx = int(0.8 * len(combined))
    
    train_data = combined[:split_idx]
    test_data = combined[split_idx:]
    
    X_train, y_train = zip(*train_data)
    X_test, y_test = zip(*test_data)
    
    print(f"Training Logistic Regression Model on {len(X_train)} samples...")
    weights, bias = train_logistic_regression(X_train, y_train)
    
    metrics = evaluate(X_test, y_test, weights, bias)
    print("\n--- Test Evaluation Results ---")
    print(f"Model Accuracy : {metrics['accuracy']}%")
    print(f"Precision      : {metrics['precision']}%")
    print(f"Recall         : {metrics['recall']}%")
    print(f"F1 Score       : {metrics['f1_score']}%")
    
    model_payload = {
        "model_type": "Logistic Regression Classifier",
        "dataset": "UCI Blood Transfusion Service Center Dataset",
        "dataset_records": len(X),
        "features": ["Recency (months)", "Frequency (times)", "Monetary (c.c.)", "Time (months)"],
        "weights": weights,
        "bias": bias,
        "means": means,
        "stds": stds,
        "metrics": metrics
    }
    
    with open(MODEL_OUT, "w", encoding="utf-8") as f:
        json.dump(model_payload, f, indent=2)
        
    print(f"\nTrained model weights and normalization parameters saved to: {MODEL_OUT}")
