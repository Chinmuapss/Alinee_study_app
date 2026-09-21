import 'package:flutter/material.dart';
import '../utils/constants.dart';
class IncidentCard extends StatelessWidget {
  const IncidentCard({required this.type, required this.onTap, super.key}); final IncidentType type; final VoidCallback onTap;
  @override Widget build(BuildContext context) => Card(child: InkWell(onTap: onTap, borderRadius: BorderRadius.circular(12), child: Padding(padding: const EdgeInsets.all(14), child: Row(children: [Text(type.emoji, style: const TextStyle(fontSize: 28)), const SizedBox(width: 12), Expanded(child: Text(type.name, style: const TextStyle(fontWeight: FontWeight.w700))), Icon(Icons.chevron_right, color: type.color)]))));
}
