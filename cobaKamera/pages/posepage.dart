import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:frontend_fisio/features/Pages/cobaKamera/bloc/poseEvent_bloc.dart';
import 'package:frontend_fisio/features/Pages/cobaKamera/bloc/posebloc.dart';
import 'package:frontend_fisio/features/Pages/cobaKamera/bloc/posestate.dart';

import 'package:frontend_fisio/features/Pages/cobaKamera/service/pose_service.dart';
import 'package:frontend_fisio/features/Pages/cobaKamera/service/pose_websocket_service.dart';
import 'package:frontend_fisio/features/Pages/cobaKamera/widget/landmark_painter.dart';

class PosePage extends StatefulWidget {
  const PosePage({super.key});

  @override
  State<PosePage> createState() => _PosePageState();
}

class _PosePageState extends State<PosePage> {
  late final PoseBloc _poseBloc;

  @override
  void initState() {
    super.initState();
    _poseBloc = PoseBloc(
      PoseService(),
      PoseWebSocketService(),
    );

    /// 🔴 START CAMERA SEKALI SAJA
    _poseBloc.add(StartCamera());
  }

  @override
  void dispose() {
    /// 🔴 WAJIB: STOP CAMERA & STREAM
    _poseBloc.add(StopCamera());
    _poseBloc.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: _poseBloc,
      child: Scaffold(
        body: BlocBuilder<PoseBloc, PoseState>(
          builder: (context, state) {
            if (state.camera == null) {
              return const Center(child: CircularProgressIndicator());
            }

            // Calculate aspect ratio. 
            // If camera is initialized, use its aspect ratio. 
            // Note: CameraController.value.aspectRatio is usually width/height.
            // In portrait mode, we might need to invert it or handle scaling carefully.
            double aspectRatio = state.camera!.value.aspectRatio;
            
            // On mobile portrait, aspect ratio is usually > 1 (e.g. 16/9), but the view is height > width.
            // CameraPreview handles this internally, but when we wrap it in AspectRatio widget,
            // we must ensure it matches the visual output.
            // Typically: 1 / aspectRatio for portrait.
            // But let's rely on standard CameraPreview behavior if we can, OR wrap everything in a Center + AspectRatio.
            
            // To ensure 1:1 mapping between CameraPreview and CustomPaint, both must be the same size.
            return Stack(
              fit: StackFit.expand,
              children: [
                Center(
                  child: CameraPreview(
                    state.camera!,
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        return GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onScaleStart: (_) {}, // Optional: Handle zoom
                          onScaleUpdate: (_) {},
                          child: (state.pose != null && state.imageSize != null)
                              ? CustomPaint(
                                  painter: LandmarkPainter(
                                    pose: state.pose!,
                                    imageSize: state.imageSize!,
                                    canvasSize: Size(constraints.maxWidth, constraints.maxHeight),
                                    isFrontCamera: state.camera!.description.lensDirection ==
                                        CameraLensDirection.front,
                                    rotation: state.rotation,
                                  ),
                                )
                              : Container(),
                        );
                      },
                    ),
                  ),
                ),
                /// RESULT PANEL
                Positioned(
                  bottom: 30,
                  left: 20,
                  right: 20,
                  child: Card(
                    color: Colors.black87,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            state.predictedLabel,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            state.feedback,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: state.feedbackColor,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 12),
                          LinearProgressIndicator(
                            value: state.confidence,
                            color: state.feedbackColor,
                            backgroundColor: Colors.grey,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            "${(state.confidence * 100).toStringAsFixed(1)}%",
                            style: const TextStyle(color: Colors.white),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
