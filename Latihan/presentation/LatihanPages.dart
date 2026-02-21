import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:camera/camera.dart';

import 'package:frontend_fisio/features/realtime_pose/painter/realtime_landmark_painter.dart';
import 'package:frontend_fisio/features/Models/JadwalModels.dart'; // Changed Import
import 'package:frontend_fisio/features/Models/pose_result.dart';
import 'package:frontend_fisio/features/Pages/Latihan/bloc/Latihan_bloc.dart';
import 'package:frontend_fisio/features/Pages/Latihan/bloc/Latihan_event.dart';
import 'package:frontend_fisio/features/Pages/Latihan/bloc/Latihan_state.dart';

// 🆕 REST OVERLAY
class _RestOverlay extends StatelessWidget {
  final ExerciseState state;
  const _RestOverlay(this.state);

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.blueGrey.withOpacity(0.95), // Opaque for rest
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.hot_tub, color: Colors.white, size: 60),
            SizedBox(height: 20),
            Text("ISTIRAHAT", style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
            SizedBox(height: 10),
            Text("Persiapan latihan berikutnya...", style: TextStyle(color: Colors.white70)),
            SizedBox(height: 30),
             Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 5),
              ),
              child: Center(
                 child: Text(
                    "${state.timer.toStringAsFixed(0)}",
                    style: TextStyle(fontSize: 50, color: Colors.white, fontWeight: FontWeight.bold),
                 ),
              ),
            ),
            SizedBox(height: 30),

          ],
        ),
      ),
    );
  }
}

class ExerciseCameraPage extends StatelessWidget {
  final JadwalDetailModel latihanData; // Changed type
  final List<JadwalDetailModel> allExercises; // Changed type

  final int currentIndex;

  const ExerciseCameraPage({
    super.key,
    required this.latihanData,
    this.allExercises = const [],
    this.currentIndex = 0,
  });

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => ExerciseBloc()
        ..add(InitCamera(
          latihanData: latihanData,
          allExercises: allExercises,
          currentIndex: currentIndex,
        )),
      child: Scaffold(
        body: BlocConsumer<ExerciseBloc, ExerciseState>(
          listener: (context, state) {
            // Handle completion
            if (state.status == 'completed') {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('✅ Latihan selesai!'),
                  backgroundColor: Colors.green,
                ),
              );
            }
            // Handle failure
            if (state.status == 'failed') {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('❌ Latihan dibatalkan'),
                  backgroundColor: Colors.red,
                ),
              );
            }
          },
          builder: (context, state) {
            return Stack(
              children: [
                _CameraView(state),
                // 🆕 SESSION SPECIFIC UI
                if (state.session == ExerciseSession.resting)
                  _RestOverlay(state)
                else ...[
                   _TopBar(state),
                   if (state.isUiVisible) _BottomInfo(state),
                ],
                
                if (state.status == 'completed' || state.status == 'failed')
                  _CompletionOverlay(state),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CameraView extends StatelessWidget {
  final ExerciseState state;

  const _CameraView(this.state);

  @override
  Widget build(BuildContext context) {
    if (!state.isCameraReady || state.cameraController == null || !state.cameraController!.value.isInitialized) {
      return Container(
        color: Colors.black,
        child: const Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
      );
    }

    // 1. Ambil ukuran preview asli dari kamera
    final Size previewSize = state.cameraController!.value.previewSize!;
    
    // 2. Cek apakah perlu swap width/height (karena orientasi sensor portrait)
    final bool isRotated = state.rotation == InputImageRotation.rotation90deg || 
                           state.rotation == InputImageRotation.rotation270deg;
                           
    final double renderWidth = isRotated ? previewSize.height : previewSize.width;
    final double renderHeight = isRotated ? previewSize.width : previewSize.height;

    return SizedBox.expand(
      child: FittedBox(
        fit: BoxFit.cover,
        child: SizedBox(
          width: renderWidth,
          height: renderHeight,
          child: Stack(
            fit: StackFit.expand,
            children: [
              CameraPreview(state.cameraController!),
              
              if (state.isPoseDetectionEnabled && 
                  state.poseResult?.pose != null && 
                  state.imageSize != null)
                LayoutBuilder(
                  builder: (context, constraints) {
                    return CustomPaint(
                      painter: RealtimeLandmarkPainter(
                        pose: state.poseResult!.pose!,
                        imageSize: state.imageSize!,
                        // 3. Pastikan Canvas Size PERSIS sama dengan Render Size
                        canvasSize: Size(renderWidth, renderHeight),
                        isFrontCamera: state.cameraController!.description.lensDirection == 
                                       CameraLensDirection.front,
                        rotation: state.rotation,
                      ),
                    );
                  }
                ),
            ],
          ),
        ),
      ),
    );
  }
}
/// Top bar dengan nama exercise dan kontrol
class _TopBar extends StatelessWidget {
  final ExerciseState state;

  const _TopBar(this.state);

  @override
  Widget build(BuildContext context) {
    final latihan = state.latihanData?.latihan; // Helper

    return Positioned(
      top: 60,
      left: 20,
      right: 20,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  latihan?.namaLatihan ?? 'Latihan', // Updated field
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    shadows: [
                      Shadow(
                        blurRadius: 2,
                        color: Colors.black54,
                        offset: Offset(1, 1),
                      ),
                    ],
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                SizedBox(
                  height: 4,
                ),
                Text(
                  'Target: ${latihan?.target.set ?? 0} set × ${latihan?.target.repetisi ?? 0} repetisi', // Updated fields
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // 🆕 Pose detection toggle
          if (state.status != 'completed' && state.status != 'failed')
            GestureDetector(
              onTap: () {
                context.read<ExerciseBloc>().add(TogglePoseDetection());
              },
              child: Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color:
                      state.isPoseDetectionEnabled ? Colors.green : Colors.grey,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Icon(
                  state.isPoseDetectionEnabled
                      ? Icons.visibility
                      : Icons.visibility_off,
                  color: Colors.white,
                  size: 24,
                ),
              ),
            ),
          const SizedBox(width: 8),
          // 🆕 UI Toggle button (Hide/Show Bottom Info)
          GestureDetector(
            onTap: () {
              context.read<ExerciseBloc>().add(ToggleUI());
            },
            child: Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: state.isUiVisible ? Colors.blue : Colors.grey,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Icon(
                state.isUiVisible ? Icons.visibility : Icons.visibility_off,
                color: Colors.white,
                size: 24,
              ),
            ),
          ),
          const SizedBox(width: 8),
          // 🆕 Flip camera button
          if (state.status != 'completed' && state.status != 'failed')
            GestureDetector(
              onTap: () {
                context.read<ExerciseBloc>().add(FlipCamera());
              },
              child: Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: Colors.purple,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.flip_camera_android,
                  color: Colors.white,
                  size: 24,
                ),
              ),
            ),
          const SizedBox(width: 8),
          // 🆕 Selesai Button
          if (state.status != 'completed' && state.status != 'failed')
            GestureDetector(
              onTap: () {
                 // Confirm dialog could be good, but for now direct action
                 context.read<ExerciseBloc>().add(CompleteExercise());
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                height: 50,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: Colors.redAccent,
                  borderRadius: BorderRadius.circular(25),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: const Text("Selesai", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ),
          const SizedBox(width: 8),
          // Start/Pause button
          // Start/Pause button
          if (state.status != 'completed' && state.status != 'failed')
            GestureDetector(
              onTap: () {
                if (state.isRunning) {
                  context.read<ExerciseBloc>().add(PauseExercise());
                } else if (state.isPaused) {
                  context.read<ExerciseBloc>().add(ResumeExercise());
                } else {
                  context.read<ExerciseBloc>().add(StartExercise());
                }
              },
              child: Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Icon(
                  state.isRunning ? Icons.pause : Icons.play_arrow,
                  color: Colors.blue,
                  size: 28,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Bottom info card dengan counter & timer
class _BottomInfo extends StatelessWidget {
  final ExerciseState state;

  const _BottomInfo(this.state);

  @override
  Widget build(BuildContext context) {
    final latihan = state.latihanData?.latihan; // Helper
    final targetRep = latihan?.target.repetisi ?? 1; // Updated
    final targetSet = latihan?.target.set ?? 1; // Updated
    
    // Duration logic: if duration is not explicitly in model, use target.waktu or fallback
    // In previous code it was target.waktu.
    // LatihanDetailModel has target.waktu.
    // However, LatihanDetailModel itself does NOT have duration anymore, mostly relies on target.waktu
    
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.95),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Row 1: Timer, Repetisi, Set (Compact)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                // Timer
                _CompactInfo(
                  icon: Icons.timer,
                  label: 'Waktu',
                  value: '${state.timer.toStringAsFixed(0)}s',
                  color: Colors.blue,
                ),
                // Repetisi
                _CompactInfo(
                  icon: Icons.repeat,
                  label: 'Rep',
                  value: '${state.repetition}/$targetRep',
                  color: Colors.orange,
                ),
                // Set
                _CompactInfo(
                  icon: Icons.fitness_center,
                  label: 'Set',
                  value: '${state.set}/$targetSet',
                  color: Colors.green,
                ),
              ],
            ),
            
            // Row 2: Pose feedback (using Socket Data)
            if (state.isPoseDetectionEnabled && state.feedback.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: state.feedbackColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: state.feedbackColor.withOpacity(0.5)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      state.isSocketValid ? Icons.check_circle : Icons.info,
                      size: 16,
                      color: state.feedbackColor,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      state.feedback,
                      style: TextStyle(
                        fontSize: 12,
                        color: state.feedbackColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '${(state.currentAccuracy * 100).toStringAsFixed(0)}%',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Compact info widget for timer/rep/set
class _CompactInfo extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _CompactInfo({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey[600],
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }
}

/// Info card kecil untuk repetisi/set
class _InfoCard extends StatelessWidget {
  final String title;
  final int current;
  final int total;
  final Color color;

  const _InfoCard({
    required this.title,
    required this.current,
    required this.total,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color, width: 2),
      ),
      child: Column(
        children: [
          Text(
            title,
            style: TextStyle(
              fontSize: 12,
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '$current/$total',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

/// Status card
class _StatusCard extends StatelessWidget {
  final String status;

  const _StatusCard({required this.status});

  @override
  Widget build(BuildContext context) {
    Color statusColor = Colors.grey;
    String statusText = 'Idle';
    IconData statusIcon = Icons.pause_circle;

    switch (status) {
      case 'running':
        statusColor = Colors.green;
        statusText = 'Berjalan';
        statusIcon = Icons.play_circle;
        break;
      case 'paused':
        statusColor = Colors.orange;
        statusText = 'Jeda';
        statusIcon = Icons.pause_circle;
        break;
      case 'completed':
        statusColor = Colors.green;
        statusText = 'Selesai';
        statusIcon = Icons.check_circle;
        break;
      case 'failed':
        statusColor = Colors.red;
        statusText = 'Batal';
        statusIcon = Icons.error;
        break;
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: statusColor, width: 2),
      ),
      child: Column(
        children: [
          Icon(statusIcon, color: statusColor, size: 24),
          const SizedBox(height: 4),
          Text(
            statusText,
            style: TextStyle(
              fontSize: 12,
              color: statusColor,
              fontWeight: FontWeight.w600,
              ),
          ),
        ],
      ),
    );
  }
}

class _CompletionOverlay extends StatelessWidget {
  final ExerciseState state;

  const _CompletionOverlay(this.state);

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black.withOpacity(0.85),
      padding: const EdgeInsets.all(24),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              state.status == 'completed' || state.status == 'allCompleted' ? Icons.emoji_events : Icons.cancel,
              color: state.status.contains('completed') ? Colors.amber : Colors.red,
              size: 80,
            ),
            const SizedBox(height: 20),
            Text(
              state.status.contains('completed')
                  ? 'Latihan Selesai!'
                  : 'Latihan Dibatalkan',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Rata-rata Akurasi: ${(state.averageAccuracy * 100).toStringAsFixed(1)}%',
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 30),
            
            // HISTORY LIST
            if (state.history.isNotEmpty) ...[
                const Align(
                    alignment: Alignment.centerLeft,
                    child: Text("Riwayat Deteksi:", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold))
                ),
                const SizedBox(height: 10),
                Expanded(
                    child: Container(
                        decoration: BoxDecoration(
                            color: Colors.white10,
                            borderRadius: BorderRadius.circular(12)
                        ),
                        child: ListView.builder(
                            itemCount: state.history.length,
                            itemBuilder: (context, index) {
                                final item = state.history[state.history.length - 1 - index]; // Reverse order
                                return ListTile(
                                    leading: Icon(
                                        item.isCorrect ? Icons.check_circle : Icons.warning,
                                        color: item.isCorrect ? Colors.green : Colors.orange
                                    ),
                                    title: Text(
                                        item.predictedLabel,
                                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)
                                    ),
                                    subtitle: Text(
                                        "Confidence: ${(item.confidence * 100).toStringAsFixed(1)}%",
                                        style: TextStyle(color: Colors.white70)
                                    ),
                                    trailing: Text(
                                        "${item.timestamp.hour}:${item.timestamp.minute}:${item.timestamp.second}",
                                        style: TextStyle(color: Colors.white38, fontSize: 12)
                                    ),
                                );
                            },
                        ),
                    ),
                ),
                const SizedBox(height: 20),
            ],

            ElevatedButton(
              onPressed: () {
                context.read<ExerciseBloc>().add(DisposeCamera());
                Navigator.pop(context);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue,
                padding: const EdgeInsets.symmetric(
                  horizontal: 40,
                  vertical: 16,
                ),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(30)
                )
              ),
              child: const Text(
                'Selesai & Keluar',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class _AccuracyCard extends StatelessWidget {
  final double currentAccuracy;
  final double averageAccuracy;
  final int correctCount;
  final int totalCount;

  const _AccuracyCard({
    required this.currentAccuracy,
    required this.averageAccuracy,
    required this.correctCount,
    required this.totalCount,
  });

  /// Get color based on accuracy level
  Color _getAccuracyColor(double accuracy) {
    if (accuracy >= 0.8) return Colors.green;
    if (accuracy >= 0.6) return Colors.orange;
    if (accuracy >= 0.4) return Colors.deepOrange;
    return Colors.red;
  }

  /// Get accuracy status text
  String _getAccuracyStatus(double accuracy) {
    if (accuracy >= 0.85) return 'Sempurna ✓';
    if (accuracy >= 0.7) return 'Bagus ✓';
    if (accuracy >= 0.5) return 'Cukup';
    return 'Perlu Perbaikan';
  }

  @override
  Widget build(BuildContext context) {
    final currentColor = _getAccuracyColor(currentAccuracy);
    final averageColor = _getAccuracyColor(averageAccuracy);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            currentColor.withOpacity(0.1),
            currentColor.withOpacity(0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: currentColor,
          width: 2,
        ),
      ),
      child: Column(
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(Icons.show_chart, color: currentColor, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    'Akurasi Gerakan',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: currentColor,
                    ),
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: currentColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  _getAccuracyStatus(currentAccuracy),
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Current Accuracy with Progress Bar
          Text(
            'Akurasi Saat Ini',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${(currentAccuracy * 100).toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: currentColor,
                    ),
                  ),
                  Text(
                    '/ 100%',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.grey[500],
                      ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: currentAccuracy.clamp(0.0, 1.0),
                  minHeight: 8,
                  backgroundColor: Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation<Color>(currentColor),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Average Accuracy & Stats
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(
                  children: [
                    Text(
                      'Rata-rata',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${(averageAccuracy * 100).toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: averageColor,
                      ),
                    ),
                  ],
                ),
                Container(
                  width: 1,
                  height: 40,
                  color: Colors.grey[300],
                ),
                Column(
                  children: [
                    Text(
                      'Gerakan Benar',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '$correctCount/$totalCount',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.green,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
