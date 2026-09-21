import 'package:flutter/material.dart';
class StatusBadge extends StatelessWidget {
  const StatusBadge(this.status, {super.key}); final String status;
  @override Widget build(BuildContext context) {
    final color = switch (status) {'PENDING' => Colors.orange, 'RESOLVED' => Colors.green, 'CANCELLED' => Colors.grey, _ => Colors.blue};
    return Chip(label: Text(status.replaceAll('_', ' '), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)), backgroundColor: color.withOpacity(.15), side: BorderSide(color: color));
  }
}
