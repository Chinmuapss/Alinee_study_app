import 'package:flutter/material.dart';
import '../utils/constants.dart';
class EmergencyButton extends StatelessWidget {
  const EmergencyButton({required this.onPressed, super.key}); final VoidCallback onPressed;
  @override Widget build(BuildContext context) => SizedBox(width: double.infinity, height: 60, child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: emergencyRed), onPressed: onPressed, icon: const Icon(Icons.sos), label: const Text('EMERGENCY REPORT', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800))));
}
