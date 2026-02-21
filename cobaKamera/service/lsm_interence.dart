import 'dart:math';
import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

class InferenceResult {
  final String label;
  final double confidence;

  InferenceResult(this.label, this.confidence);
}

class LSTMInference {
  late Interpreter _interpreter;
  List<String> labels = [];
  bool _isInitialized = false;

  Future<void> loadModel() async {
    try {
      print('📦 [LSTM] Loading model...');

      // Load interpreter
      _interpreter =
          await Interpreter.fromAsset('assets/models/pose_model_lstm_lutut.tflite');
      print('✅ [LSTM] Model loaded successfully');

      // Load labels
      try {
        final labelsData =
            await rootBundle.loadString('assets/models/labels_lstm_lutut.txt');
        labels = labelsData
            .split(RegExp(r'\r?\n'))
            .map((e) => e.trim())
            .where((e) => e.isNotEmpty)
            .toList();

        print('✅ [LSTM] Loaded ${labels.length} labels: $labels');
      } catch (e) {
        print('⚠️ [LSTM] Error loading labels, using defaults: $e');
        labels = ['child_pose', 'standing_shoulder', 'standing_wall'];
      }

      _isInitialized = true;
      print('✅ [LSTM] Inference service ready');
    } catch (e) {
      print('❌ [LSTM] Error loading model: $e');
      rethrow;
    }
  }

  Future<InferenceResult> predict(List<List<double>> sequence) async {
    if (!_isInitialized) {
      throw Exception('Model not initialized. Call loadModel() first.');
    }

    try {
      if (sequence.isEmpty) {
        return InferenceResult('Not Ready', 0.0);
      }

      // Shape: [1, 15, 132]
      // The interpreter.run expects input of shape [1, 15, 132]
      // We must construct it as List<List<List<double>>>

      // 1. Pad or trim sequence to exactly 15 frames
      List<List<double>> processedSequence = List.from(sequence);
      if (processedSequence.length < 15) {
        // Pad with zeros (132 zeros per frame)
        while (processedSequence.length < 15) {
          processedSequence.add(List.filled(132, 0.0));
        }
      } else if (processedSequence.length > 15) {
        // Take last 15 frames
        processedSequence = processedSequence.sublist(processedSequence.length - 15);
      }

      // 2. Wrap in batch dimension: [1, 15, 132]
      final input = [processedSequence]; 
      
      final output =
          List.filled(labels.length, 0.0).reshape([1, labels.length]);

      print('🎯 [LSTM] Running inference with input shape: [1, ${processedSequence.length}, ${processedSequence[0].length}]');
      _interpreter.run(input, output);

      // Parse output
      final scores = List<double>.from(output[0]);
      final maxIdx = scores.indexOf(scores.reduce(max));

      final resultLabel = maxIdx < labels.length ? labels[maxIdx] : 'Unknown';
      final confidence = scores[maxIdx];

      print(
          '✨ [LSTM] Prediction: $resultLabel (${(confidence * 100).toStringAsFixed(1)}%)');

      return InferenceResult(resultLabel, confidence);
    } catch (e) {
      print('❌ [LSTM] Prediction error: $e');
      return InferenceResult('Error', 0.0);
    }
  }

  void dispose() {
    _interpreter.close();
    _isInitialized = false;
    print('🔌 [LSTM] Disposed');
  }
}
