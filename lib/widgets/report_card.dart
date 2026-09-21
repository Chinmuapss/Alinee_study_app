import 'package:flutter/material.dart';
import '../models/report.dart';
import 'status_badge.dart';
class ReportCard extends StatelessWidget {
  const ReportCard({required this.report, this.onTap, super.key}); final IncidentReport report; final VoidCallback? onTap;
  @override Widget build(BuildContext context) => Card(child: ListTile(onTap: onTap, leading: const CircleAvatar(child: Icon(Icons.report)), title: Text('${report.reportId} • ${report.incidentType}', style: const TextStyle(fontWeight: FontWeight.bold)), subtitle: Text('${report.createdLabel}\n${report.latitude.toStringAsFixed(5)}, ${report.longitude.toStringAsFixed(5)}'), isThreeLine: true, trailing: StatusBadge(report.status)));
}
