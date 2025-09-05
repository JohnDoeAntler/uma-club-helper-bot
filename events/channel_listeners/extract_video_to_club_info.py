import asyncio
import time
import discord
import os
from datetime import datetime

from opencv.club_video_parsing import extract_video
from utils.blocking import run_blocking
from utils.spreadsheet import get_service
import uuid
from datetime import timezone

async def update_progress_message(logger_message, start_time):
    """Updates the progress message every 5 seconds"""
    progress_dots = ["", ".", "..", "..."]
    dot_index = 0
    
    while True:
        await asyncio.sleep(5)
        elapsed = time.time() - start_time
        minutes, seconds = divmod(int(elapsed), 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        try:
            await logger_message.edit(content=f"processing video{progress_dots[dot_index]} (elapsed: {time_str})")
            dot_index = (dot_index + 1) % len(progress_dots)
        except discord.NotFound:
            break
        except discord.HTTPException:
            break

async def process_video_file(bot, file_path, logger_message):
    """Extract club member data from video file"""
    start = time.time()
    progress_task = None
    
    try:
        progress_task = asyncio.create_task(update_progress_message(logger_message, start))
        response = await run_blocking(bot, extract_video, file_path)
        end = time.time()
        
        if progress_task:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
        
        return response, end - start
    except Exception as e:
        if progress_task:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
        raise e

def format_data_for_codeblock(member_data):
    """Format extracted data for code block output"""
    if not member_data:
        return "", ""
    
    names = []
    total_fans = []
    for member in member_data:
        # name
        name = member['name'].replace('"', '""')
        name = f'"{name}"'
        names.append(name)
        # total fans
        total_fans.append(member['total_fans'])

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    header_line = ','.join([''] + names)
    data_line = ','.join([current_time] + total_fans)
    
    return header_line, data_line

def _get_current_utc_timestamp():
    """Get current UTC timestamp formatted for spreadsheet"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def _extract_member_names_and_fans(member_data):
    """Extract names and fan counts from member data"""
    names = [member['name'] for member in member_data]
    total_fans = [str(member['total_fans']) for member in member_data]
    return names, total_fans

def _validate_spreadsheet_format(header_row):
    """Validate that spreadsheet has correct format"""
    if not header_row or header_row[0] != 'Timestamp':
        return False, "Invalid spreadsheet format - first column should be 'Timestamp'"
    return True, None

def _map_member_data_to_columns(member_data, existing_names, current_time):
    """Map member data to spreadsheet columns, handling new members"""
    header_row = ['Timestamp'] + existing_names.copy()
    new_row = [current_time] + [''] * len(existing_names)
    
    for member in member_data:
        member_name = member['name']
        total_fans = str(member['total_fans'])
        
        if member_name in existing_names:
            col_index = existing_names.index(member_name) + 1
            new_row[col_index] = total_fans
        else:
            # New member - add column
            header_row.append(member_name)
            new_row.append(total_fans)
    
    return header_row, new_row

def _create_new_spreadsheet(sheet, spreadsheet_id, member_data, current_time):
    """Create initial spreadsheet with headers and first data row"""
    names, total_fans = _extract_member_names_and_fans(member_data)
    header_row = ['Timestamp'] + names
    data_row = [current_time] + total_fans
    
    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range='A1:ZZ2',
        valueInputOption='RAW',
        body={'values': [header_row, data_row]}
    ).execute()
    
    return len(names)

def _update_existing_spreadsheet(sheet, spreadsheet_id, values, member_data, current_time):
    """Update existing spreadsheet with new data row"""
    header_row = values[0]
    is_valid, error_msg = _validate_spreadsheet_format(header_row)
    if not is_valid:
        return False, error_msg, 0
    
    existing_names = header_row[1:]  # Skip timestamp column
    updated_header, new_row = _map_member_data_to_columns(member_data, existing_names, current_time)
    
    # Update header row (always update to handle new members)
    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range='A1:ZZ1',
        valueInputOption='RAW',
        body={'values': [updated_header]}
    ).execute()
    
    # Add new data row
    next_row = len(values) + 1
    sheet.values().update(
        spreadsheetId=spreadsheet_id,
        range=f'A{next_row}:ZZ{next_row}',
        valueInputOption='RAW',
        body={'values': [new_row]}
    ).execute()
    
    new_members_count = len(updated_header) - len(header_row)
    return True, None, new_members_count

def _get_spreadsheet_data(sheet, spreadsheet_id):
    """Fetch existing spreadsheet data"""
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range='A:ZZ'
    ).execute()
    return result.get('values', [])

def _format_success_message(spreadsheet_url, member_count, new_members_count, is_new_sheet):
    """Format success message based on operation type"""
    base_msg = f"Created new spreadsheet with {member_count} members: {spreadsheet_url}" if is_new_sheet else f"Updated spreadsheet with {member_count} members: {spreadsheet_url}"
    
    if not is_new_sheet and new_members_count > 0:
        base_msg += f" ({new_members_count} new columns added)"
    
    return base_msg

async def update_spreadsheet(club, member_data):
    """Update Google Sheets with extracted data"""
    if not club.spreadsheet_id or not member_data:
        return False, "No spreadsheet ID or no data to update"

    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{club.spreadsheet_id}"
    current_time = _get_current_utc_timestamp()
    
    try:
        service = get_service()
        sheet = service.spreadsheets()
        values = _get_spreadsheet_data(sheet, club.spreadsheet_id)
        
        if not values or not values[0]:
            # Empty spreadsheet
            member_count = _create_new_spreadsheet(sheet, club.spreadsheet_id, member_data, current_time)
            message = _format_success_message(spreadsheet_url, member_count, 0, is_new_sheet=True)
            return True, message
        else:
            # Existing spreadsheet
            success, error_msg, new_members_count = _update_existing_spreadsheet(
                sheet, club.spreadsheet_id, values, member_data, current_time
            )
            
            if not success:
                return False, error_msg
            
            message = _format_success_message(spreadsheet_url, len(member_data), new_members_count, is_new_sheet=False)
            return True, message
    
    except Exception as e:
        return False, f"Spreadsheet update failed: {str(e)}"

async def extract_video_to_club_info(bot, message: discord.Message, club):
    if len(message.attachments) == 0:
        await message.channel.send("No attachments found, expected a video recording of the club info.")
        return

    attachment = message.attachments[0]

    if not attachment.content_type.startswith("video/"):
        await message.channel.send("The attachment is not a video, expected a video recording of the club info.")
        return

    logger = await message.channel.send("downloading video...")

    file_path = f'./downloads/{uuid.uuid4()}.{attachment.content_type.split("/")[1]}'

    try:
        await attachment.save(file_path)
    except Exception as e:
        await logger.edit(content=f"Failed to download video: {e}")
        return

    await logger.edit(content="downloaded video, start processing...")
    
    try:
        # Extract data from video
        member_data_per_chunk, processing_time = await process_video_file(bot, file_path, logger)
        # flat the list from {}[][] to {}[]
        member_data = [item for sublist in member_data_per_chunk for item in sublist]
        
        if club.spreadsheet_id:
            # Club has spreadsheet enabled
            await logger.edit(content=f"processed in {processing_time:.1f} seconds, updating spreadsheet...")
            
            success, message_text = await update_spreadsheet(club, member_data)
            
            if success:
                await logger.edit(content=f"{message_text}\nProcessed in {processing_time:.1f} seconds")
            else:
                await logger.edit(content=f"Processing completed in {processing_time:.1f} seconds, but spreadsheet update failed: {message_text}")
        else:
            # Club doesn't have spreadsheet enabled - show code block
            header_line, data_line = format_data_for_codeblock(member_data)
            
            codeblock = f"```\n{header_line}\n{data_line}\n```"
            
            await logger.edit(content=f"Processed in {processing_time:.1f} seconds\n\n{codeblock}")
            
    except Exception as e:
        await logger.edit(content=f"Failed to process video: {e}")
    finally:
        os.remove(file_path)
